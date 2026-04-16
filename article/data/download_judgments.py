"""Download large judgment files from HuggingFace.

These files are too large for GitHub and are hosted at:
https://huggingface.co/datasets/Butanium/persona-negation-judgments
"""

from pathlib import Path
from huggingface_hub import hf_hub_download

REPO_ID = "Butanium/persona-negation-judgments"
DATA_DIR = Path(__file__).parent

FILES = {
    "data/v2-split/judgments.parquet": "v2_judgments.parquet",
    "data/v3-split/judgments.parquet": "v3_judgments.parquet",
}


def main():
    for repo_path, local_name in FILES.items():
        dest = DATA_DIR / local_name
        if dest.exists():
            print(f"  {local_name} already exists, skipping")
            continue
        print(f"  Downloading {local_name}...")
        hf_hub_download(
            repo_id=REPO_ID,
            filename=repo_path,
            repo_type="dataset",
            local_dir=DATA_DIR,
            local_dir_use_symlinks=False,
        )
        # Move from nested path to flat
        downloaded = DATA_DIR / repo_path
        downloaded.rename(dest)
        print(f"  Saved to {dest}")

    # Clean up empty HF dirs
    for d in (DATA_DIR / "data" / "v2-split", DATA_DIR / "data" / "v3-split", DATA_DIR / "data"):
        if d.exists() and not any(d.iterdir()):
            d.rmdir()


if __name__ == "__main__":
    main()
