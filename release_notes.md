# GeodeSync v2.3.6 — Fix a problem

## Simple troubleshooting in the app

Choose **Fix a problem** in the bottom bar. Run **Check Setup** for a read-only Steam/game check, or paste the exact Windows or Steam error and choose **Explain Error**. For common problems, GeodeSync gives direct steps. If it does not recognize the error, it says so and points to the support report instead of guessing.

The Windows setup check validates the Geometry Dash executable and DLL formats before launch. If Windows shows an error and the game does not start, GeodeSync can notice the failed launch and open the troubleshooter. macOS launch failures open the same guidance window.

**Copy Steps** copies the instructions for support chat. **Export Report** saves system status, recent activity, and the last error entered in the troubleshooter. The report is local; review it before sharing. It does not contain save-file contents or mod files.

The troubleshooting scan is read-only. It never downloads replacement DLLs, disables security software, or changes game files by itself. Steam Verify is recommended when game files appear damaged.

## Verification

The automated suite includes tests for the Windows `0xc000007b` / Bad Image guidance, the Python runtime extraction error, unknown errors, and read-only setup findings. GitHub Actions runs the Windows regression suite and builds Windows, macOS, and Linux packages.
