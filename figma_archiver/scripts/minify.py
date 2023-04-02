import json
import click
import random
from tqdm import tqdm
from pathlib import Path


def minify_json_file(input_file_path: Path, output_file_path: Path):
    try:
        with input_file_path.open('r') as input_file, output_file_path.open('w') as output_file:
            data = json.load(input_file)
            json.dump(data, output_file, separators=(',', ':'))
    except KeyboardInterrupt:
        output_file_path.unlink(missing_ok=True)
        tqdm("Keyboard interrupt detected. Removing incomplete output file.")
        raise
    except Exception as e:
        output_file_path.unlink(missing_ok=True)
        raise e



@click.command()
@click.argument('input_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--pattern', default='*.json', help='Pattern to look for JSON files.')
@click.option('--output', default=None, help='Output directory. If not specified, use the input directory.')
@click.option('--output-pattern', default='{key}.min.json', help='Pattern for the output file.')
@click.option('--max', default=None, type=int, help='Maximum number of items to process.')
@click.option('--shuffle', is_flag=True, help='Shuffle the target files for even distribution.')
def minify_json_directory(input_dir, pattern, output, output_pattern, max, shuffle):
    input_dir = Path(input_dir)
    if not output:
        output = input_dir
    else:
        output = Path(output)

    output.mkdir(parents=True, exist_ok=True)
    json_files = sorted(list(input_dir.glob(pattern)))

    # Check for minified files
    search_pattern = output_pattern.format(key="*")
    # check if there are already minified files (if the parent path is different)
    # if the parent path is the same, we will check if the file has been minified, in the main loop
    # to be more accurate, we actually have to check the patterns as well, but for simplicity, we will just check the parent path, otherwise, let it handle in the main loop
    if input_dir.resolve().samefile(output.resolve()):
        minified_files = set()
    else:
      minified_files = set(output.rglob(search_pattern))
    
    minified_files = {f.stem for f in minified_files}
    json_files = [f for f in json_files if f.stem not in minified_files]

    if shuffle:
        random.shuffle(json_files)

    if max is not None:
        json_files = json_files[:max]

    total_saved_space = 0
    with tqdm(json_files, desc='📦') as progress:
      for file_path in progress:

          already_minified = False
          file_key = file_path.stem
          output_file_name = Path(output_pattern.format(key=file_key))
          output_file_path = output / output_file_name

          # check if input and output are same (overwrite)
          if output_file_path.exists() and file_path.resolve().samefile(output_file_path.resolve()):
              # check if the output file has been minified, by checking if it has only one line
              with output_file_path.open('r') as f:
                  if len(f.readlines()) == 1:
                      # skip this file
                      already_minified = True

          if already_minified:
              tqdm.write(f"📦 Skipping {output_file_name} (already minified)")
          else:
              output_file_path.parent.mkdir(parents=True, exist_ok=True)

              minify_json_file(file_path, output_file_path)
              saved_space = file_path.stat().st_size - output_file_path.stat().st_size
              saved_space_mb = saved_space / (1024 * 1024)
              total_saved_space += saved_space_mb
              tqdm.write(f"📦 Saved {saved_space_mb:.2f} MB for {output_file_name}")
              progress.desc = f"📦 Saved {(total_saved_space / 1024):.2f} GB"

if __name__ == '__main__':
    minify_json_directory()
