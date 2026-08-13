using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Net.Http;
using System.Text;
using System.Text.Json;

namespace DocTools.Services;

/// <summary>GitHub Release 的最新版信息。</summary>
public sealed class UpdateInfo
{
    public string TagName { get; init; } = "";
    public string ZipUrl { get; init; } = "";
    public long ZipSize { get; init; }

    public string Version => TagName.TrimStart('v', 'V');
}

/// <summary>
/// 轻量自动更新：查 GitHub Releases → 下载 zip → 校验 → 通过临时批处理
/// 在退出后替换 DocTools.exe 与 docserver\ 再重启。
/// 只发布单一 win-x64 包，无飞鼠那种多渠道误推更新的复杂度。
/// </summary>
public sealed class UpdateService
{
    private const string RepoApi = "https://api.github.com/repos/pyrrolys1ne/DocTools/releases/latest";
    private const string AssetName = "DocTools-win-x64.zip";
    private static readonly HttpClient Http = CreateClient();

    public Version CurrentVersion { get; } =
        typeof(UpdateService).Assembly.GetName().Version ?? new Version(1, 0, 0);

    private static HttpClient CreateClient()
    {
        var client = new HttpClient { Timeout = TimeSpan.FromSeconds(30) };
        client.DefaultRequestHeaders.UserAgent.ParseAdd("DocTools-Desktop/1.0");
        return client;
    }

    /// <summary>查询最新 Release；无更新、网络失败或解析失败时返回 null（不打扰）。</summary>
    public async Task<UpdateInfo?> CheckForUpdateAsync(CancellationToken ct = default)
    {
        try
        {
            using var resp = await Http.GetAsync(RepoApi, ct);
            if (!resp.IsSuccessStatusCode)
            {
                return null;
            }

            using var doc = JsonDocument.Parse(await resp.Content.ReadAsStringAsync(ct));
            var root = doc.RootElement;
            var tag = root.TryGetProperty("tag_name", out var t) ? t.GetString() ?? "" : "";
            if (!tag.StartsWith('v'))
            {
                return null;
            }

            if (!Version.TryParse(tag.TrimStart('v', 'V'), out var latest) || latest <= CurrentVersion)
            {
                return null;
            }

            if (!root.TryGetProperty("assets", out var assets))
            {
                return null;
            }

            foreach (var asset in assets.EnumerateArray())
            {
                var name = asset.TryGetProperty("name", out var n) ? n.GetString() ?? "" : "";
                if (!name.Equals(AssetName, StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                var url = asset.TryGetProperty("browser_download_url", out var u) ? u.GetString() ?? "" : "";
                var size = asset.TryGetProperty("size", out var s) ? s.GetInt64() : 0;
                if (string.IsNullOrEmpty(url))
                {
                    return null;
                }

                return new UpdateInfo { TagName = tag, ZipUrl = url, ZipSize = size };
            }

            return null;
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"Update check failed: {ex.Message}");
            return null;
        }
    }

    /// <summary>
    /// 下载并准备更新：校验 zip 魔数与大小 → 解压 → 写 update.cmd。
    /// 返回批处理路径；调用方启动它并立即退出应用，替换与重启由批处理完成。
    /// </summary>
    public async Task<string> DownloadAndInstallAsync(UpdateInfo info, CancellationToken ct = default)
    {
        var tempRoot = Path.Combine(Path.GetTempPath(), "doctools-update");
        Directory.CreateDirectory(tempRoot);
        var zipPath = Path.Combine(tempRoot, AssetName);
        var extractDir = Path.Combine(tempRoot, "extracted");
        if (Directory.Exists(extractDir))
        {
            Directory.Delete(extractDir, recursive: true);
        }

        using (var resp = await Http.GetAsync(info.ZipUrl, HttpCompletionOption.ResponseHeadersRead, ct))
        {
            resp.EnsureSuccessStatusCode();
            await using var fs = File.Create(zipPath);
            await resp.Content.CopyToAsync(fs, ct);
        }

        var head = new byte[2];
        await using (var fs = File.OpenRead(zipPath))
        {
            await fs.ReadAsync(head, ct);
        }

        if (head[0] != 0x50 || head[1] != 0x4B)
        {
            throw new InvalidDataException("下载的更新包不是有效的 zip 文件");
        }

        if (info.ZipSize > 0 && new FileInfo(zipPath).Length != info.ZipSize)
        {
            throw new InvalidDataException("更新包大小与发布不一致，已中止");
        }

        ZipFile.ExtractToDirectory(zipPath, extractDir);
        if (!File.Exists(Path.Combine(extractDir, "DocTools.exe")))
        {
            throw new InvalidDataException("更新包缺少 DocTools.exe");
        }

        if (!Directory.Exists(Path.Combine(extractDir, "docserver")))
        {
            throw new InvalidDataException("更新包缺少 docserver\\");
        }

        // update.cmd：等主程序退出 → 杀掉残留 docserver → 替换 → 重启 → 自删
        var appDir = AppContext.BaseDirectory;
        var cmdPath = Path.Combine(tempRoot, "update.cmd");
        var script =
            "@echo off\r\n" +
            "timeout /t 3 /nobreak >nul\r\n" +
            "taskkill /f /im DocTools.exe >nul 2>&1\r\n" +
            "taskkill /f /im docserver.exe >nul 2>&1\r\n" +
            $"xcopy /e /y /q \"{extractDir}\\docserver\\*\" \"{appDir}\\docserver\\\" >nul 2>&1\r\n" +
            $"copy /y \"{extractDir}\\DocTools.exe\" \"{appDir}\\DocTools.exe\" >nul\r\n" +
            $"start \"\" \"{appDir}\\DocTools.exe\"\r\n" +
            "del \"%~f0\"\r\n";
        await File.WriteAllTextAsync(cmdPath, script, Encoding.ASCII, ct);
        return cmdPath;
    }
}
