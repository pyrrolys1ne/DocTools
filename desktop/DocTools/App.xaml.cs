using System.Windows;
using DocTools.Services;
using DocTools.ViewModels;

namespace DocTools;

public partial class App : Application
{
    private DocServer? _server;
    private AppSettings? _settings;

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        var settings = AppSettings.Load();
        _settings = settings;
        ThemeManager.Init(settings.Theme);
        try
        {
            // 拉起随包分发的本地 API 服务，客户端与后端通过 localhost HTTP 通信。
            _server = new DocServer();
            _server.Start();
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                $"无法启动本地服务：{ex.Message}",
                "DocTools",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
            Shutdown(1);
            return;
        }

        var viewModel = new MainViewModel(new DocToolsApi(_server.BaseUrl), settings);
        var window = new MainWindow { DataContext = viewModel };
        MainWindow = window;
        window.Show();
        // 后台拉取引擎能力清单（office 等），据此禁用不可用操作；失败不打扰
        _ = viewModel.LoadCapabilitiesAsync();
        // 启动静默检查更新（受设置 CheckForUpdates 控制）
        _ = viewModel.CheckForUpdatesSilentlyAsync();
    }

    protected override void OnExit(ExitEventArgs e)
    {
        _settings?.Save();
        _server?.Dispose();
        base.OnExit(e);
    }
}
