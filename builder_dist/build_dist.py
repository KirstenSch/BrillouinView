#!/usr/bin/env python3
"""
Cross-platform build script using UV package manager
Supports Windows, Linux, and macOS
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path



def clean_build_dirs():
    """Remove previous build artifacts"""
    dirs_to_clean = ["build", "dist"]
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}/")
            shutil.rmtree(dir_name)



def get_python_executable():
    """Get the path to the Python executable in the UV venv"""
    if platform.system() == "Windows":
        return Path(".venv/Scripts/python.exe")
    else:
        return Path(".venv/bin/python")


def build_executable(entry_point="main.py", app_name="myapp", include_ui=True):
    """
    Build executable using PyInstaller with UV environment
    
    Args:
        entry_point: Path to your main Python file
        app_name: Name of the output executable
        onefile: If True, creates a single executable file
        include_ui: If True, includes UI files
    """
    if not os.path.exists(entry_point):
        print(f"Error: Entry point '{entry_point}' not found!")
        sys.exit(1)
    
    python_exe = get_python_executable()

    print(f"Building executable...")

    # Basic PyInstaller command using UV's Python
    cmd = [
        "pyinstaller",
        "--clean",
        f"--name={app_name}",
    ]

    # Add UI files if present
    if include_ui:
        ui_files = list(Path(".").glob("*.ui"))
        for ui_file in ui_files:
            cmd.extend(["--add-data", f"{ui_file}{os.pathsep}ui"])
        
        # Add resources if present
        if os.path.exists("resources"):
            cmd.extend(["--add-data", f"resources{os.pathsep}resources"])
    
    # Platform-specific options
    if platform.system() == "Darwin":
        # macOS: Create .app bundle
        cmd.extend([
            "--windowed",
            "--osx-bundle-identifier", f"com.yourcompany.{app_name}"
        ])
    elif platform.system() == "Windows":
        # Windows: windowed mode (no console) and icon
        cmd.append("--windowed")
        if os.path.exists("icon.ico"):
            cmd.append("--icon=icon.ico")
    else:
        # Linux: windowed mode
        cmd.append("--windowed")
    
    # Hidden imports for PyQt5
    cmd.extend([
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=PyQt5.uic",
    ])
    
    cmd.append(entry_point)
    
    # Run PyInstaller
    print(f"Running command: {' '.join(cmd)}")
    subprocess.check_call(cmd)
    
    print(f"✓ Build complete! Executable in dist/ directory")


def create_release_package():
    """Package the executable for distribution"""
    dist_dir = Path("dist")
    
    if not dist_dir.exists():
        print("No dist directory found!")
        return
    
    # Create release directory
    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)
    
    # Copy executable(s) to release directory
    for item in dist_dir.iterdir():
        dest = release_dir / f"{item.name}"
        if item.is_file():
            shutil.copy2(item, dest)
        elif item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
    
    print(f"✓ Release package created in release/ directory")


def main():
    """Main build process"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build executable using UV")
    parser.add_argument("--entry-point", default="main.py", 
                       help="Entry point Python file (default: main.py)")
    parser.add_argument("--name", default="myapp",
                       help="Name of the executable (default: myapp)")
    parser.add_argument("--no-clean", action="store_true",
                       help="Don't clean build directories before building")
    parser.add_argument("--onedir", action="store_true",
                       help="Create one-directory bundle instead of one-file")

    args = parser.parse_args()

    
    if not args.no_clean:
        clean_build_dirs()
    
    
    build_executable(
        entry_point=args.entry_point,
        app_name=args.name,
        onefile=not args.onedir
    )
    # Optional: create release package 
    # create_release_package()
    
    print("\n" + "="*50)
    print(f"Build successful!")
    print("="*50)


if __name__ == "__main__":
    main()
