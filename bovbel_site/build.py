import shutil
from pathlib import Path


COMMON_STATIC_DIR = Path(__file__).parent.parent / "sites" / "common"


def prepare_output(output_dir, static_dir=None):
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    if COMMON_STATIC_DIR.exists():
        shutil.copytree(COMMON_STATIC_DIR, output_dir, dirs_exist_ok=True)

    if static_dir and static_dir.exists():
        shutil.copytree(static_dir, output_dir, dirs_exist_ok=True)
