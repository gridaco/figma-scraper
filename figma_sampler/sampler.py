from urllib.parse import urlparse
import json
import shutil
from pathlib import Path
import click
from tqdm import tqdm
import jsonlines
from colorama import Fore, Back, Style


@click.command()
@click.option('--index', required=True, type=click.Path(exists=True), help='Path to index file (JSONL)')
@click.option('--map', required=True, type=click.Path(exists=True), help='Path to map file (JSON)')
@click.option('--meta', required=True, type=click.Path(exists=True), help='Path to meta file (JSON)')
@click.option('--output', required=True, type=click.Path(), help='Path to output directory')
@click.option('--dir-files-archive', required=True, type=str, help='Path to files archive directory')
@click.option('--dir-images-archive', required=True, type=str, help='Path to images archive directory')
@click.option('--sample', default=None, type=int, help='Number of samples to process')
@click.option('--sample-all', is_flag=False, help='Process all available data')
@click.option('--ensure-images', is_flag=False, help='Ensure images exists for files')
def main(index, map, meta, output, dir_files_archive, dir_images_archive, sample, sample_all, ensure_images):
    # Read index file
    with jsonlines.open(index, mode='r') as reader:
        # get id, link, title
        index_data = [(obj["id"], obj["link"], obj["title"]) for obj in reader]

    # Read map file
    with open(map, 'r') as f:
        map_data = json.load(f)

    # Read meta file
    with open(meta, 'r') as f:
        # it is a array of objects with id, name, description, version, ...
        meta_data = json.load(f)
        # now, convert it to key-value pair with id as key
        meta_data = {obj["id"]: obj for obj in meta_data}

    dir_files_archive = Path(dir_files_archive)
    dir_images_archive = Path(dir_images_archive)

    # create root output dir
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)

    tqdm.write(f"📂 {output}")

    # locate the already-sampled files with finding map.json files
    # get the ids of the already-sampled files
    completes = [x.parent.name for x in output.glob('**/map.json')]

    # pre-validate the targtes (check if drafted file exists for community lunk)
    available = [(id, link, _) for id, link, _ in index_data
                 if link in map_data and map_data[link] is not None]

    # remove the already-sampled files from the available list
    available = [x for x in available if x[0] not in completes]

    # Calculate sample size
    if sample_all:
        sample_size = len(available)
    else:
        sample_size = sample if sample is not None else len(available)

    targets = available[:sample_size]

    # Process samples with tqdm progress bar
    for id, link, title in tqdm(targets, desc='🗳️', leave=True, colour='white'):
        try:
            file_url = map_data[link]

            file_key = extract_file_key(file_url)
            output_dir: Path = output / id

            # If the output directory already exists, remove it
            if output_dir.exists():
                shutil.rmtree(output_dir)
            # and create a new one
            output_dir.mkdir(parents=False, exist_ok=False)

            # Copy file.json
            try:
                shutil.copy(dir_files_archive /
                        f"{file_key}.json", output_dir / "file.json")
            except FileNotFoundError as e:
                shutil.rmtree(output_dir)
                raise SamplerException(id, file_key, f"File not found for sample <{title}>")

            # Copy images
            images_archive_dir = dir_images_archive / file_key
            if images_archive_dir.exists():
              shutil.copytree(images_archive_dir, output_dir / "images")
            else:
              if ensure_images:
                raise OkException(id, file_key, f"Images not found for sample <{title}>")

            # Write meta.json
            with open(output_dir / "meta.json", "w") as f:
                try:
                  meta = meta_data[id]
                except KeyError:
                  raise OkException(id, file_key, f"Meta not found for sample <{title}>")
                json.dump(meta, f)

            # Write map.json
            with open(output_dir / "map.json", "w") as f:
                json.dump({"latest": meta_data[id]["version"], "versions": {
                          meta_data[id]["version"]: file_key}}, f)

            tqdm.write(Fore.WHITE + f"☑ {id} → {output_dir} ({file_key} / {title})")
        except OkException as e:
            tqdm.write(Fore.YELLOW + f'☒ {e.id} → {output_dir} WARNING ({e.file}) - {e.message}')
        except SamplerException as e:
            tqdm.write(Fore.RED + f"☒ {e.id}/{file_key} - {e.message}")
            output_dir.exists() and shutil.rmtree(output_dir)
        except Exception as e:
            tqdm.write(Fore.RED + f"☒ {id}/{file_key} - ERROR sampleing <{title}>")
            output_dir.exists() and shutil.rmtree(output_dir)
            raise e

class SamplerException(Exception):
    def __init__(self, id, file, message):
        self.message = message
        self.id = id
        self.file = file

class OkException(SamplerException):
    ...

def extract_file_key(url):
    """
    Extracts the file key from a Figma file URL.

    For example, if the file url is "https://www.figma.com/file/ckoLxKa4EKf3CaPq609rpa/Material-3-Design-Kit-(Community)?t=VSv529MHpDOG6ZmU-0"

    After splitting the path with the / delimiter, the resulting list is
    ['', 'file', 'ckoLxKa4EKf3CaPq609rpa', ...].
    The file key is at index [2] (the third element) in the list.
    """
    path = urlparse(url).path
    file_key = path.split('/')[2]
    return file_key


if __name__ == '__main__':
    main()
