using System.IO;
using System.Text.Json;

namespace DocTools.Services;

/// <summary>本地用户设置：主题与每个操作最近使用的路径（存 %AppData%\DocTools）。</summary>
public sealed class AppSettings
{
    public string Theme { get; set; } = "";

    /// <summary>启动时静默检查更新（默认开；手动"检查更新"按钮不受此开关限制）。</summary>
    public bool CheckForUpdates { get; set; } = true;

    /// <summary>MinerU API 地址（自建 mineru-api，留空则默认官方 mineru.net）。</summary>
    public string MineruApiUrl { get; set; } = "";

    /// <summary>MinerU Token（mineru.net 官方 Token，或自建服务的鉴权 Token）。</summary>
    public string MineruToken { get; set; } = "";

    public Dictionary<string, string> Sources { get; set; } = new();

    public Dictionary<string, string> Outputs { get; set; } = new();

    private static string Dir =>
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "DocTools");

    private static string FilePath => Path.Combine(Dir, "settings.json");

    public static AppSettings Load()
    {
        try
        {
            if (File.Exists(FilePath))
            {
                return JsonSerializer.Deserialize<AppSettings>(File.ReadAllText(FilePath)) ?? new AppSettings();
            }
        }
        catch
        {
            // 配置损坏时回退到默认值
        }
        return new AppSettings();
    }

    public void Save()
    {
        try
        {
            Directory.CreateDirectory(Dir);
            File.WriteAllText(FilePath, JsonSerializer.Serialize(this));
        }
        catch
        {
            // 保存失败不影响使用
        }
    }
}
