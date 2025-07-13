import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import List, Optional

# Daily development workflow
# python build_lambda.py                      # Build all
# python build_lambda.py function --force     # Force function rebuild
# python build_lambda.py layer --arch amd64   # Switch architecture

# # CI/CD pipeline
# python build_lambda.py --force --arch arm64 # Always rebuild everything

# # Quick iterations
# python build_lambda.py websocket            # Just WebSocket function
# python build_lambda.py clean                # Clean all

# Build cdk app
# clear; mvn clean install; cdk synth
# cdk deploy
# cdk deploy --all --require-approval never

# Configuration
ROOT = Path(__file__).parent.resolve()
LAYER_DIR = ROOT / "resources" / "layers"
FUNCTION_DIR = ROOT / "resources" / "lambda"
VOCAB_PROCESSOR_SRC = ROOT.parent / "agent"
HANDLER_SRC = VOCAB_PROCESSOR_SRC / "handlers"
CACHE_DIR = ROOT / ".build_cache"

# Build artifacts
LAYER_ZIP = LAYER_DIR / "lambda_requirements_layer.zip"
FUNCTION_ZIP = FUNCTION_DIR / "vocab_processor_zip.zip"
WEBSOCKET_ZIP = FUNCTION_DIR / "websocket_handler_zip.zip"

# Default configuration
DEFAULT_ARCH = "arm64"
DEFAULT_PYTHON_VERSION = "3.12"


class BuildMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.layer_size = 0
        self.function_size = 0
        self.websocket_size = 0

    def elapsed(self) -> float:
        return time.time() - self.start_time

    def report(self):
        print(f"\n{'='*50}")
        print(f"📊 Build Summary")
        print(f"{'='*50}")
        print(f"⏱️  Total time: {self.elapsed():.2f}s")
        print(f"📦 Layer size: {self.layer_size / 1024 / 1024:.1f}MB")
        print(f"🔧 Function size: {self.function_size / 1024 / 1024:.1f}MB")
        print(f"🔌 WebSocket size: {self.websocket_size / 1024 / 1024:.1f}MB")
        print(
            f"💾 Total size: {(self.layer_size + self.function_size + self.websocket_size) / 1024 / 1024:.1f}MB"
        )


def run(
    cmd: List[str], cwd: Optional[Path] = None, timeout: int = 300
) -> subprocess.CompletedProcess:
    """Enhanced command runner with timeout and better error handling."""
    print(f"🔧 {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, check=True, cwd=cwd, timeout=timeout, capture_output=True, text=True
        )
        return result
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Command timed out after {timeout}s: {' '.join(cmd)}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(cmd)}")
        print(f"💥 Error: {e.stderr}")
        raise


def calculate_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    if not file_path.exists():
        return ""

    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def calculate_dir_hash(dir_path: Path, extensions: List[str] = None) -> str:
    """Calculate hash of directory contents."""
    if not dir_path.exists():
        return ""

    extensions = extensions or [".py", ".txt", ".yml", ".yaml", ".json"]
    hasher = hashlib.sha256()

    for file_path in sorted(dir_path.rglob("*")):
        if file_path.is_file() and any(file_path.suffix == ext for ext in extensions):
            hasher.update(str(file_path.relative_to(dir_path)).encode())
            hasher.update(calculate_hash(file_path).encode())

    return hasher.hexdigest()


def should_rebuild(cache_key: str, dependencies: List[Path]) -> bool:
    """Check if rebuild is needed based on dependency changes."""
    cache_file = CACHE_DIR / f"{cache_key}.json"

    if not cache_file.exists():
        return True

    try:
        with open(cache_file, "r") as f:
            cache_data = json.load(f)

        for dep_path in dependencies:
            current_hash = (
                calculate_hash(dep_path)
                if dep_path.is_file()
                else calculate_dir_hash(dep_path)
            )
            cached_hash = cache_data.get(str(dep_path), "")

            if current_hash != cached_hash:
                print(f"🔄 Dependency changed: {dep_path}")
                return True

        return False
    except (json.JSONDecodeError, KeyError):
        return True


def update_cache(cache_key: str, dependencies: List[Path]):
    """Update build cache with current dependency hashes."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / f"{cache_key}.json"

    cache_data = {}
    for dep_path in dependencies:
        current_hash = (
            calculate_hash(dep_path)
            if dep_path.is_file()
            else calculate_dir_hash(dep_path)
        )
        cache_data[str(dep_path)] = current_hash

    with open(cache_file, "w") as f:
        json.dump(cache_data, f, indent=2)


def build_layer(architecture: str = DEFAULT_ARCH, force: bool = False) -> bool:
    """Build Lambda layer with smart caching."""
    print(f"🏗️  Building Lambda layer for {architecture}...")

    requirements_file = VOCAB_PROCESSOR_SRC / "requirements_lambda.txt"
    dependencies = [requirements_file]

    if not force and not should_rebuild("layer", dependencies):
        print(f"✅ Layer is up to date, skipping build")
        return False

    python_target = LAYER_DIR / "python"
    if python_target.exists():
        shutil.rmtree(python_target)
    python_target.mkdir(parents=True, exist_ok=True)

    # Enhanced Docker command with caching
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        f"--platform=linux/{architecture}",
        "--entrypoint",
        "",
        "-v",
        f"{requirements_file.resolve()}:/var/task/requirements.txt:ro",
        "-v",
        f"{python_target.resolve()}:/opt/python:rw",
        f"public.ecr.aws/lambda/python:{DEFAULT_PYTHON_VERSION}",
        "sh",
        "-c",
        "pip install --no-cache-dir --compile -r /var/task/requirements.txt -t /opt/python && "
        "find /opt/python -name '*.pyc' -delete && "
        "find /opt/python -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true && "
        "chmod -R 755 /opt/python",
    ]

    run(docker_cmd)

    # Enhanced pruning
    prune_layer_advanced(python_target)

    # Create optimized zip
    if LAYER_ZIP.exists():
        LAYER_ZIP.unlink()

    zip_directory_optimized(python_target, LAYER_ZIP, root_folder_name="python")

    # Update cache
    update_cache("layer", dependencies)

    print(f"✅ Layer built successfully: {LAYER_ZIP.name}")
    return True


def build_function(force: bool = False) -> bool:
    """Build main Lambda function with caching."""
    print("🏗️  Building Lambda function...")

    dependencies = [
        HANDLER_SRC / "vocab_handler.py",
        VOCAB_PROCESSOR_SRC / "vocab_processor",
        VOCAB_PROCESSOR_SRC / "__init__.py",
    ]

    if not force and not should_rebuild("function", dependencies):
        print("✅ Function is up to date, skipping build")
        return False

    zip_root = FUNCTION_DIR / "vocab_processor"
    if zip_root.exists():
        shutil.rmtree(zip_root)
    zip_root.mkdir(parents=True, exist_ok=True)

    # Copy files with validation
    _copy_with_validation(VOCAB_PROCESSOR_SRC / "__init__.py", zip_root / "__init__.py")

    _copy_with_validation(
        HANDLER_SRC / "vocab_handler.py", zip_root / "lambda_handler.py"
    )

    # Copy vocab_processor package
    vocab_processor_pkg = zip_root / "vocab_processor"
    vocab_processor_pkg.mkdir()

    _copy_package(VOCAB_PROCESSOR_SRC / "vocab_processor", vocab_processor_pkg)

    # Create optimized zip
    if FUNCTION_ZIP.exists():
        FUNCTION_ZIP.unlink()

    zip_directory_optimized(zip_root, FUNCTION_ZIP)

    # Update cache
    update_cache("function", dependencies)

    print(f"✅ Function built successfully: {FUNCTION_ZIP.name}")
    return True


def build_websocket_function(force: bool = False) -> bool:
    """Build WebSocket Lambda function with caching."""
    print("🏗️  Building WebSocket Lambda function...")

    dependencies = [
        HANDLER_SRC / "websocket_handler.py",
        VOCAB_PROCESSOR_SRC / "vocab_processor",
        VOCAB_PROCESSOR_SRC / "__init__.py",
    ]

    if not force and not should_rebuild("websocket", dependencies):
        print("✅ WebSocket function is up to date, skipping build")
        return False

    zip_root = FUNCTION_DIR / "websocket_handler"
    if zip_root.exists():
        shutil.rmtree(zip_root)
    zip_root.mkdir(parents=True, exist_ok=True)

    # Copy files with validation
    _copy_with_validation(VOCAB_PROCESSOR_SRC / "__init__.py", zip_root / "__init__.py")

    _copy_with_validation(
        HANDLER_SRC / "websocket_handler.py", zip_root / "websocket_handler.py"
    )

    # Copy vocab_processor package
    vocab_processor_pkg = zip_root / "vocab_processor"
    vocab_processor_pkg.mkdir()

    _copy_package(VOCAB_PROCESSOR_SRC / "vocab_processor", vocab_processor_pkg)

    # Create optimized zip
    if WEBSOCKET_ZIP.exists():
        WEBSOCKET_ZIP.unlink()

    zip_directory_optimized(zip_root, WEBSOCKET_ZIP)

    # Update cache
    update_cache("websocket", dependencies)

    print(f"✅ WebSocket function built successfully: {WEBSOCKET_ZIP.name}")
    return True


def _copy_with_validation(src: Path, dst: Path):
    """Copy file with existence validation."""
    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {src}")
    shutil.copy2(src, dst)


def _copy_package(src_dir: Path, dst_dir: Path):
    """Copy Python package with selective file inclusion."""
    if not src_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {src_dir}")

    for item in src_dir.iterdir():
        if item.name.startswith("."):
            continue

        if item.is_dir():
            if item.name not in {"__pycache__", ".pytest_cache", "tests", "test"}:
                shutil.copytree(item, dst_dir / item.name)
        else:
            if item.suffix in {".py", ".json", ".txt", ".yml", ".yaml"}:
                shutil.copy2(item, dst_dir / item.name)


def prune_layer_advanced(target_dir: Path):
    """Conservative layer pruning - only remove things we're 100% sure are safe."""
    print(f"🧹 Optimizing layer size: {target_dir}")

    # Only remove file extensions we're absolutely sure are safe
    unwanted_file_extensions = {
        ".pyc",
        ".pyo",
        ".pyd",  # Compiled Python files
        ".DS_Store",
        "Thumbs.db",  # OS files
    }

    # Only remove directories we're absolutely sure are safe
    unwanted_dirs = {
        "__pycache__",  # Python cache
        ".pytest_cache",  # Pytest cache
        "tests",  # Test directories
        "test",  # Test directories
        ".git",  # Version control
        ".svn",  # Version control
        ".hg",  # Version control
    }

    # Only remove files with test patterns we're sure about
    test_file_patterns = {
        "**/test_*.py",  # test_something.py
        "**/*_test.py",  # something_test.py
        "**/conftest.py",  # pytest config
    }

    total_removed = 0

    for root, dirs, files in os.walk(target_dir, topdown=False):
        root_path = Path(root)

        # Remove unwanted file extensions and test files
        for file in files:
            file_path = root_path / file
            should_remove = False

            # Check file extensions
            if file_path.suffix in unwanted_file_extensions:
                should_remove = True

            # Check if it's a test file
            if any(file_path.match(pattern) for pattern in test_file_patterns):
                should_remove = True

            if should_remove:
                try:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    total_removed += size
                except Exception as e:
                    print(f"⚠️  Could not remove {file_path}: {e}")

        # Remove unwanted directories
        for dir_name in dirs:
            if dir_name in unwanted_dirs:
                dir_path = root_path / dir_name
                try:
                    size = sum(
                        f.stat().st_size for f in dir_path.rglob("*") if f.is_file()
                    )
                    shutil.rmtree(dir_path)
                    total_removed += size
                except Exception as e:
                    print(f"⚠️  Could not remove {dir_path}: {e}")

    print(f"🗑️  Removed {total_removed / 1024 / 1024:.1f}MB of unnecessary files")


def zip_directory_optimized(folder: Path, zip_path: Path, root_folder_name: str = None):
    """Create optimized ZIP with better compression."""
    print(f"📦 Creating optimized ZIP: {zip_path.name}")

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for file_path in folder.rglob("*"):
            if file_path.is_file():
                if root_folder_name:
                    arcname = Path(root_folder_name) / file_path.relative_to(folder)
                else:
                    arcname = file_path.relative_to(folder)
                zipf.write(file_path, arcname)

    size = zip_path.stat().st_size
    print(f"✅ Created {zip_path.name} ({size / 1024 / 1024:.1f}MB)")
    return size


def clean_all():
    """Clean all build artifacts and cache."""
    print("🧹 Cleaning build artifacts...")

    artifacts = [
        LAYER_DIR / "python",
        FUNCTION_DIR / "vocab_processor",
        FUNCTION_DIR / "websocket_handler",
        LAYER_ZIP,
        FUNCTION_ZIP,
        WEBSOCKET_ZIP,
        CACHE_DIR,
    ]

    for artifact in artifacts:
        if artifact.exists():
            if artifact.is_dir():
                shutil.rmtree(artifact)
            else:
                artifact.unlink()
            print(f"🗑️  Removed: {artifact}")


def build_parallel(architecture: str, force: bool = False) -> BuildMetrics:
    """Build all components in parallel where possible."""
    metrics = BuildMetrics()

    print(f"🚀 Starting parallel build for {architecture} architecture...")

    # Build layer first (functions may depend on it)
    layer_rebuilt = build_layer(architecture, force)

    # Build functions in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        function_future = executor.submit(build_function, force)
        websocket_future = executor.submit(build_websocket_function, force)

        function_rebuilt = function_future.result()
        websocket_rebuilt = websocket_future.result()

    # Collect metrics
    if LAYER_ZIP.exists():
        metrics.layer_size = LAYER_ZIP.stat().st_size
    if FUNCTION_ZIP.exists():
        metrics.function_size = FUNCTION_ZIP.stat().st_size
    if WEBSOCKET_ZIP.exists():
        metrics.websocket_size = WEBSOCKET_ZIP.stat().st_size

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Lambda Build Tool")
    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=["all", "layer", "function", "websocket", "clean"],
        help="Build command",
    )
    parser.add_argument(
        "--arch",
        default=DEFAULT_ARCH,
        choices=["arm64", "amd64"],
        help="Target architecture",
    )
    parser.add_argument(
        "--force", "-f", action="store_true", help="Force rebuild even if cached"
    )
    parser.add_argument(
        "--parallel",
        "-p",
        action="store_true",
        default=True,
        help="Use parallel builds",
    )

    args = parser.parse_args()

    try:
        if args.command == "clean":
            clean_all()
        elif args.command == "all":
            if args.parallel:
                metrics = build_parallel(args.arch, args.force)
                metrics.report()
            else:
                build_layer(args.arch, args.force)
                build_function(args.force)
                build_websocket_function(args.force)
        elif args.command == "layer":
            build_layer(args.arch, args.force)
        elif args.command == "function":
            build_function(args.force)
            build_websocket_function(args.force)
        elif args.command == "websocket":
            build_websocket_function(args.force)

        print("\n🎉 Build completed successfully!")

    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
