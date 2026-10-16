# One-file repair for missing assets/manifest.json

The uploaded Windows log shows Python 3.12.7 x64 and package installation pass, followed by a missing assets/manifest.json failure at build step 4. No PyInstaller run occurred. The pip upgrade notice is not the failure.

Replace only `scripts/build_support.py` in the existing `VideoDownloader-source` folder with the file in `VideoDownloader-build-support-fix.zip`. Keep `.venv-build` and all other files. Run `BUILD_WINDOWS_EXE.bat` again.

The replacement preserves existing interfaces. It downloads and verifies the missing FFmpeg binaries and matching upstream source, assembles assets in a temporary folder, generates the manifest, and publishes that folder only after validation. Valid existing assets are reused without downloading; unknown existing files are not overwritten. Checksums remain pinned, TLS verification remains enabled, and damaged downloads are not used. Setup progress/errors appear in the existing timestamped build logs.

Binary: Gyan FFmpeg 6.1.1 essentials x64, SHA-256 `742e32fc9f92681f9f254b925e1b613fdd8074ba40749d4879aefdb009b94cc5`, from Microsoft's historical winget manifest.

Source: upstream FFmpeg n6.1.1, SHA-512 `a84209fe36a2a0262ebc34b727e7600b12d4739991a95599d7b4df533791b12e2e43586ccc6ff26aab2f935a3049866204e322ec0c5e49e378fc175ded34e183`, from Microsoft's vcpkg 2024.02.14 recipe. Source-archive scope is explicitly upstream FFmpeg only; additional vendor dependency/build sources are not assembled or represented as complete.

Both actual archives were downloaded and matched the independent published checksums. Asset preparation and repeat-run reuse succeeded with those actual archives. All 48 local regression tests pass. The new tests cover cached preparation, checksum rejection, and preservation of existing files. This verifies preparation, not execution of the Windows binaries on this Linux machine. The user's next Windows build must run the local and bundled runtime/media checks before any EXE success claim.
