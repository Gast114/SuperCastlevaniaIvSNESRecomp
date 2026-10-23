"""Fetch pinned, public image-edit weights into new ComfyUI subdirectories.

No package install, environment modification, server restart or inference.
Original models are never replaced. Interrupted .partial files can resume.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--comfy-models", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    root = args.comfy_models.resolve()
    progress = {"status": "downloading", "gpu_used": False, "uploads": False, "files": []}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    def report():
        tmp = args.report.with_suffix(".tmp")
        tmp.write_text(json.dumps(progress, indent=2) + "\n", encoding="utf-8")
        tmp.replace(args.report)
    report()
    try:
        for spec in manifest["files"]:
            target = (root / spec["target"]).resolve()
            target.relative_to(root)
            record = {**spec, "path": str(target)}
            progress["files"].append(record)
            if target.exists():
                if target.stat().st_size != spec["size"] or sha256(target) != spec["sha256"]:
                    raise FileExistsError("Do not overwrite a different existing model: " + str(target))
                record["status"] = "verified_existing"
                report()
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_suffix(target.suffix + ".partial")
            size = partial.stat().st_size if partial.exists() else 0
            if size > spec["size"]:
                raise ValueError("Unexpected oversized partial download: " + str(partial))
            if size < spec["size"]:
                url = f'https://huggingface.co/{spec["repo"]}/resolve/{spec["revision"]}/{spec["file"]}'
                req = Request(url, headers={"Range": f"bytes={size}-"} if size else {})
                with urlopen(req, timeout=90) as response:
                    if size and response.status != 206:
                        # Only our explicitly named partial file is restarted.
                        size = 0
                    last = 0.
                    with partial.open("ab" if size else "wb") as stream:
                        while chunk := response.read(8 * 1024 * 1024):
                            stream.write(chunk)
                            size += len(chunk)
                            if time.monotonic() - last > 2:
                                record.update(status="downloading", received=size)
                                report()
                                last = time.monotonic()
            if partial.stat().st_size != spec["size"] or sha256(partial) != spec["sha256"]:
                raise ValueError("Downloaded model failed length/SHA256 validation: " + str(partial))
            if target.exists():
                raise FileExistsError("Model appeared during download: " + str(target))
            partial.replace(target)
            record.update(status="verified", received=size)
            report()
            print("Verified " + spec["target"], flush=True)
        progress["status"] = "complete"
        report()
    except Exception as exc:
        progress.update(status="failed", error=str(exc))
        report()
        raise


if __name__ == "__main__":
    main()
