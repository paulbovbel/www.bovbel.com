import shutil


def prepare_output(output_dir, static_dir=None):
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    if static_dir and static_dir.exists():
        shutil.copytree(static_dir, output_dir, dirs_exist_ok=True)
