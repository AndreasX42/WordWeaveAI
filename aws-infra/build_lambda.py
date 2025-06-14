import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
LAYER_DIR = ROOT / "resources" / "layers"
FUNCTION_DIR = ROOT / "resources" / "lambda"
VOCAB_PROCESSOR_SRC = ROOT.parent / "vocab_processor"

LAYER_ZIP = LAYER_DIR / "vocab_processor_requirements_layer.zip"
FUNCTION_ZIP = FUNCTION_DIR / "vocab_processor_zip.zip"


def run(cmd, cwd=None):
    print(f"{cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=cwd, shell=isinstance(cmd, str))


def build_layer():
    print("Building Lambda layer...")
    python_target = LAYER_DIR / "python"
    if python_target.exists():
        shutil.rmtree(python_target)
    python_target.mkdir(parents=True, exist_ok=True)

    # Determine absolute paths for Docker volume mounting
    abs_req_path = (VOCAB_PROCESSOR_SRC / "requirements.txt").resolve()
    abs_layer_path = python_target.resolve()

    # Install dependencies using Docker to match Lambda environment
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "--entrypoint",
        "",
        "-v",
        f"{abs_req_path}:/var/task/requirements_lambda.txt:ro",
        "-v",
        f"{abs_layer_path}:/opt/python:rw",
        "public.ecr.aws/lambda/python:3.11",
        "sh",
        "-c",
        "pip install -r /var/task/requirements_lambda.txt -t /opt/python && chmod -R 755 /opt/python",
    ]
    run(docker_cmd)

    # Run prune_layer.sh if it exists
    prune_layer(python_target)

    # Zip the layer
    if LAYER_ZIP.exists():
        LAYER_ZIP.unlink()

    zip_directory_with_folder(python_target, LAYER_ZIP, root_folder_name="python")


def build_function():
    print("Building Lambda function...")

    zip_root = FUNCTION_DIR / "vocab_processor"  # This will be zipped as root/
    if zip_root.exists():
        shutil.rmtree(zip_root)
    zip_root.mkdir(parents=True, exist_ok=True)

    # This is the directory where quiz_generator will be copied *as a folder*
    vocab_processor_pkg = zip_root / "vocab_processor"
    vocab_processor_pkg.mkdir()

    # Copy necessary subfolders
    for name in ["api", "commons", "quiz_generation", "tests"]:
        shutil.copytree(VOCAB_PROCESSOR_SRC / name, vocab_processor_pkg / name)

    # Copy root-level files
    for filename in ["__init__.py", "lambda_function.py"]:
        shutil.copy(VOCAB_PROCESSOR_SRC / filename, vocab_processor_pkg / filename)

    # Zip the package with quiz_generator/ as the root
    if FUNCTION_ZIP.exists():
        FUNCTION_ZIP.unlink()
    zip_directory_with_folder(zip_root, FUNCTION_ZIP, root_folder_name=None)


def clean():
    print("Cleaning up...")
    shutil.rmtree(LAYER_DIR / "python", ignore_errors=True)
    shutil.rmtree(FUNCTION_DIR / "vocab_processor", ignore_errors=True)
    LAYER_ZIP.unlink(missing_ok=True)
    FUNCTION_ZIP.unlink(missing_ok=True)


def prune_layer(target_dir: Path):
    print(f"Cleaning up layer directory: {target_dir}")

    for root, dirs, files in os.walk(target_dir, topdown=False):
        # Remove files
        for file in files:
            full_path = Path(root) / file
            if file.endswith((".pyc", ".pyo", ".log")) or file == ".DS_Store":
                try:
                    full_path.unlink()
                    print(f"Removed file: {full_path}")
                except Exception as e:
                    print(f"Failed to delete file {full_path}: {e}")

        # Remove directories
        for dir in dirs:
            full_path = Path(root) / dir
            if dir in {"__pycache__", "test", "tests", ".pytest_cache"}:
                try:
                    shutil.rmtree(full_path)
                    print(f"Removed dir: {full_path}")
                except Exception as e:
                    print(f"Failed to remove dir {full_path}: {e}")

    print("Cleanup done.")


def zip_directory_with_folder(
    folder: Path, zip_path: Path, root_folder_name: str = None
):
    print(f"Zipping {folder} as root folder → {zip_path}")
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in folder.rglob("*"):
            if root_folder_name:
                arcname = Path(root_folder_name) / file.relative_to(folder)
            else:
                arcname = file.relative_to(folder)
            zipf.write(file, arcname)
    print(f"Created {zip_path.name}")


def main():
    if len(sys.argv) == 1:
        build_layer()
        build_function()
    elif sys.argv[1] == "layer":
        build_layer()
    elif sys.argv[1] == "function":
        build_function()
    elif sys.argv[1] == "clean":
        clean()
    else:
        print("Usage: python build.py [layer|function|clean]")


if __name__ == "__main__":
    main()
