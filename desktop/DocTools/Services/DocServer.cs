using System.Diagnostics;
using System.IO;

namespace DocTools.Services;

/// <summary>
/// 管理随包分发的 docserver.exe：以子进程拉起（--port 0 自动选端口），
/// 从 stdout 读取 DOCSERVER_PORT= 拿到实际端口；退出时关闭子进程。
/// </summary>
public sealed class DocServer : IDisposable
{
    private Process? _process;

    public Uri BaseUrl { get; private set; } = null!;

    public void Start()
    {
        var exeDir = AppContext.BaseDirectory;
        var exe = new[]
            {
                Path.Combine(exeDir, "docserver", "docserver.exe"),
                Path.Combine(exeDir, "docserver.exe"),
            }
            .FirstOrDefault(File.Exists)
            ?? throw new FileNotFoundException(
                "找不到 docserver.exe，请确认它与 DocTools.exe 位于同一目录（或 docserver\\ 子目录）。");

        var psi = new ProcessStartInfo
        {
            FileName = exe,
            Arguments = "--port 0",
            WorkingDirectory = Path.GetDirectoryName(exe)!,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
        };
        _process = Process.Start(psi) ?? throw new InvalidOperationException("无法启动 docserver 进程。");

        const string prefix = "DOCSERVER_PORT=";
        string? line;
        while ((line = _process.StandardOutput.ReadLine()) is not null)
        {
            if (line.StartsWith(prefix, StringComparison.Ordinal) &&
                int.TryParse(line[prefix.Length..], out var port))
            {
                BaseUrl = new Uri($"http://127.0.0.1:{port}/api/v1/");
                return;
            }
        }
        // stdout 读到 EOF 说明进程启动失败，把 stderr 内容带出来便于排错。
        var detail = _process.StandardError.ReadToEnd();
        throw new InvalidOperationException($"docserver 启动失败：{detail}");
    }

    public void Dispose()
    {
        if (_process is not null)
        {
            try
            {
                if (!_process.HasExited)
                {
                    _process.Kill();
                    _process.WaitForExit(5000);
                }
            }
            catch
            {
                // 进程可能已退出，忽略。
            }
            _process.Dispose();
            _process = null;
        }
    }
}
