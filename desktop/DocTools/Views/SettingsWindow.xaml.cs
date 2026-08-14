using System.Windows;
using DocTools.ViewModels;

namespace DocTools.Views;

public partial class SettingsWindow : Window
{
    public SettingsWindow()
    {
        InitializeComponent();
    }

    private MainViewModel ViewModel => (MainViewModel)DataContext;

    private void SaveClick(object sender, RoutedEventArgs e)
    {
        ViewModel.SaveMineruSettings();
        Close();
    }

    private void CancelClick(object sender, RoutedEventArgs e) => Close();
}
