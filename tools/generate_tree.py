import os

def generate_tree(start_path="."):
    for root, dirs, files in os.walk(start_path):
        level = root.replace(start_path, "").count(os.sep)
        indent = " " * 3 * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = " " * 3 * (level + 1)
        for f in files:
            print(f"{sub_indent}{f}")

if __name__ == "__main__":
    generate_tree("..")
