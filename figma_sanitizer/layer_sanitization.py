import concurrent.futures
import glob
import json
import os

remove_keywords = [
    "Arrow", "Ellipse", "Frame", "Group", "Line", "Polygon", "Rectangle", "Star", "Vector"
]

def remove_nodes_with_keywords(node, keywords):
    if 'children' in node:
        node['children'] = [
            child for child in node['children']
            if not any(keyword in child['name'] for keyword in keywords)
        ]
        for child in node['children']:
            remove_nodes_with_keywords(child, keywords)

def process_json_file(json_file, keywords):
    with open(json_file, 'r') as f:
        json_data = json.load(f)

    remove_nodes_with_keywords(json_data, keywords)

    with open(json_file, 'w') as f:
        json.dump(json_data, f, indent=4)

def main():
    folder_pattern = "../data/samples/figma-samples-5k.min/*"
    folders = [folder for folder in glob.glob(folder_pattern) if os.path.isdir(folder)]
    json_files = [os.path.join(folder, "file.json") for folder in folders]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = [executor.submit(process_json_file, json_file, remove_keywords) for json_file in json_files]

        for future in concurrent.futures.as_completed(results):
            try:
                future.result()
            except Exception as e:
                print(f"An error occurred while processing a JSON file: {e}")

if __name__ == "__main__":
    main()
