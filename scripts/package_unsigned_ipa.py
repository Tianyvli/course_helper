"""Package a Flutter device build, preserving executable modes and symlinks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import stat
import struct
import zipfile

VERSION = "1.2.0"
UPSTREAM_COMMIT = "900ed39b05dcec2386a14a2a636eaceb2173d68a"
BUNDLE_ID = "com.anerycoft.coursehelper"
PRIVACY_KEYS = (
    "NSCameraUsageDescription", "NSPhotoLibraryUsageDescription",
    "NSPhotoLibraryAddUsageDescription", "NSLocationWhenInUseUsageDescription",
)


def validate_device_executable(data):
    if len(data) < 32 or data[:4] != b"\xcf\xfa\xed\xfe":
        raise ValueError("Expected a thin 64-bit Mach-O device executable")
    _, cpu, _, filetype, commands, _, _, _ = struct.unpack_from("<8I", data)
    if cpu != 0x0100000C or filetype != 2:
        raise ValueError("Expected an arm64 executable")
    offset = 32
    device_platform = False
    for _ in range(commands):
        command, size = struct.unpack_from("<2I", data, offset)
        if size < 8 or offset + size > len(data):
            raise ValueError("Invalid Mach-O load command")
        if command == 0x32:  # LC_BUILD_VERSION
            platform = struct.unpack_from("<I", data, offset + 8)[0]
            if platform != 2:  # PLATFORM_IOS; simulator is 7
                raise ValueError("Executable is not built for an iOS device")
            device_platform = True
        elif command == 0x25:  # LC_VERSION_MIN_IPHONEOS
            device_platform = True
        offset += size
    if not device_platform:
        raise ValueError("Missing iOS device platform load command")


def validate_ipa(ipa_path):
    with zipfile.ZipFile(ipa_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("IPA checksum verification failed")
        if any(not name.startswith("Payload/Runner.app/") for name in archive.namelist()):
            raise ValueError("Unexpected files outside Payload/Runner.app")
        root = "Payload/Runner.app/"
        info = plistlib.loads(archive.read(root + "Info.plist"))
        if info["CFBundleIdentifier"] != BUNDLE_ID:
            raise ValueError("Unexpected Bundle ID")
        if info["CFBundleShortVersionString"] != VERSION:
            raise ValueError("Unexpected app version")
        for key in PRIVACY_KEYS:
            if not info.get(key):
                raise ValueError(f"Missing privacy description: {key}")
        executable = archive.getinfo(root + info["CFBundleExecutable"])
        if not (executable.external_attr >> 16) & stat.S_IXUSR:
            raise ValueError("Executable permission was not preserved")
        validate_device_executable(archive.read(executable))
        if root + "Frameworks/App.framework/App" not in archive.namelist():
            raise ValueError("Missing Flutter App.framework")
        if root + "embedded.mobileprovision" in archive.namelist():
            raise ValueError("Expected an unsigned build without a provisioning profile")
        return info


def package(app_path, output_path):
    app_path, output_path = Path(app_path), Path(output_path)
    if app_path.name != "Runner.app" or not app_path.is_dir():
        raise ValueError("Expected a Runner.app device build")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(app_path.rglob("*")):
            if path.is_dir() and not path.is_symlink():
                continue
            name = "Payload/Runner.app/" + path.relative_to(app_path).as_posix()
            mode = path.lstat().st_mode
            entry = zipfile.ZipInfo(name)
            entry.create_system = 3
            entry.external_attr = mode << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            data = os.readlink(path).encode() if stat.S_ISLNK(mode) else path.read_bytes()
            archive.writestr(entry, data)
    info = validate_ipa(output_path)
    with output_path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    output_path.with_suffix(".ipa.sha256").write_text(
        f"{digest}  {output_path.name}\n", encoding="utf-8"
    )
    metadata = {
        "version": info["CFBundleShortVersionString"],
        "build_number": info["CFBundleVersion"],
        "bundle_id": info["CFBundleIdentifier"],
        "minimum_ios": info.get("MinimumOSVersion"),
        "architecture": "arm64", "signed": False,
        "upstream_commit": UPSTREAM_COMMIT,
        "build_commit": os.environ.get("GITHUB_SHA"),
        "run_url": (
            f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/"
            f"{os.environ['GITHUB_RUN_ID']}"
        ) if os.environ.get("GITHUB_RUN_ID") else None,
        "sha256": digest,
        "baidu_key_source": "repository variable" if os.environ.get("BAIDU_IOS_MAP_AK") else "upstream (unverified)",
        "device_tests": "Not performed; sign and install on an iPhone to verify features.",
    }
    output_path.with_suffix(".build.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", default="build/ios/iphoneos/Runner.app")
    parser.add_argument("--output", default="dist/CourseHelper_1.2.0_unsigned.ipa")
    args = parser.parse_args()
    print(json.dumps(package(args.app, args.output), indent=2, ensure_ascii=False))
