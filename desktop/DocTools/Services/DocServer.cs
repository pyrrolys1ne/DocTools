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

    public void Start(AppSettings? settings = null)
    {
        var exe = ResolveExecutablePath();
        if (exe is null)
        {
            throw new FileNotFoundException(
                "找不到 docserver.exe。发布包应包含 docserver\\docserver.exe；开发运行请先执行 packaging\\build_server.ps1。\n" +
                $"已检查：{string.Join("；", CandidatePaths())}");
        }

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
        InjectMineruEnv(psi, settings);
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

    /// <summary>重启 docserver（应用新的 MinerU 等配置），返回新的 BaseUrl。</summary>
    public Uri Restart(AppSettings settings)
    {
        Dispose();
        Start(settings);
        return BaseUrl;
    }

    private static void InjectMineruEnv(ProcessStartInfo psi, AppSettings? settings)
    {
        if (settings is null)
        {
            return;
        }

        var apiUrl = settings.MineruApiUrl.Trim();
        var token = settings.MineruToken.Trim();
        // 只填 Token（key）时默认走官方 mineru.net，实现"填一个 key 就能用"。
        if (string.IsNullOrWhiteSpace(apiUrl) && !string.IsNullOrWhiteSpace(token))
        {
            apiUrl = "https://mineru.net/api/v4";
        }

        if (!string.IsNullOrWhiteSpace(apiUrl))
        {
            psi.EnvironmentVariables["DOCTOOLS_MINERU_API_URL"] = apiUrl;
        }
        if (!string.IsNullOrWhiteSpace(token))
        {
            psi.EnvironmentVariables["DOCTOOLS_MINERU_TOKEN"] = token;
        }
    }

    private static string? ResolveExecutablePath()
        => CandidatePaths().FirstOrDefault(File.Exists);

    private static IEnumerable<string> CandidatePaths()
    {
        var roots = new List<string>();
        AddRoot(roots, Path.GetDirectoryName(Environment.ProcessPath));
        AddRoot(roots, AppContext.BaseDirectory);
        AddRoot(roots, Directory.GetCurrentDirectory());

        // 正式包：服务端与客户端同目录，或位于 docserver 子目录。
        foreach (var root in roots)
        {
            yield return Path.Combine(root, "docserver", "docserver.exe");
            yield return Path.Combine(root, "docserver.exe");
        }

        // 开发运行：dotnet run 的输出目录不包含 PyInstaller 服务端，
        // 从输出目录向上寻找仓库 dist\\docserver\\docserver.exe。
        foreach (var root in roots)
        {
            var directory = new DirectoryInfo(root);
            for (var depth = 0; directory is not null && depth < 8; depth++, directory = directory.Parent)
            {
                yield return Path.Combine(directory.FullName, "dist", "docserver", "docserver.exe");
            }
        }
    }

    private static void AddRoot(List<string> roots, string? root)
    {
        if (!string.IsNullOrWhiteSpace(root) && !roots.Contains(root, StringComparer.OrdinalIgnoreCase))
        {
            roots.Add(root);
        }
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
