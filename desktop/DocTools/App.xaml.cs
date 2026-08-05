using System.Windows;
using DocTools.Services;
using DocTools.ViewModels;

namespace DocTools;

public partial class App : Application
{
    private DocServer? _server;

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
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

        var viewModel = new MainViewModel(new DocToolsApi(_server.BaseUrl));
        var window = new MainWindow { DataContext = viewModel };
        MainWindow = window;
        window.Show();
    }

    protected override void OnExit(ExitEventArgs e)
    {
        _server?.Dispose();
        base.OnExit(e);
    }
}