using System.Windows;
using DocTools.Services;
using DocTools.ViewModels;

namespace DocTools;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
    }

    private MainViewModel ViewModel => (MainViewModel)DataContext;

    private void MinimizeClick(object sender, RoutedEventArgs e) => WindowState = WindowState.Minimized;

    private void MaximizeClick(object sender, RoutedEventArgs e) =>
        WindowState = WindowState == WindowState.Maximized ? WindowState.Normal : WindowState.Maximized;

    private void CloseClick(object sender, RoutedEventArgs e) => Close();

    private void ThemeClick(object sender, RoutedEventArgs e)
    {
        ThemeManager.Toggle();
        ViewModel.Settings.Theme = ThemeManager.Current;
        ViewModel.Settings.Save();
    }

    private void DiagnosticsClick(object sender, RoutedEventArgs e) => ViewModel.ExportDiagnostics();

    private void CheckUpdatesClick(object sender, RoutedEventArgs e) => ViewModel.CheckForUpdates();

    private void OnDragOver(object sender, DragEventArgs e)
    {
        e.Effects = e.Data.GetDataPresent(DataFormats.FileDrop) ? DragDropEffects.Copy : DragDropEffects.None;
        e.Handled = true;
    }

    private void OnDrop(object sender, DragEventArgs e)
    {
        if (e.Data.GetData(DataFormats.FileDrop) is string[] paths && paths.Length > 0)
        {
            ViewModel.SourcePath = paths[0];
        }
    }
}
