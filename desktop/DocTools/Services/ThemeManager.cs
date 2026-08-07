using System.Windows;
using Microsoft.Win32;

namespace DocTools.Services;

/// <summary>浅色/深色主题：通过调整 App 级两个配色字典的合并顺序实现（后合并者生效）。</summary>
public static class ThemeManager
{
    public const string Light = "Light";
    public const string Dark = "Dark";

    public static string Current { get; private set; } = Light;

    public static void Init(string? savedTheme)
    {
        Apply(string.IsNullOrWhiteSpace(savedTheme) ? SystemTheme() : savedTheme);
    }

    public static void Toggle()
    {
        Apply(Current == Light ? Dark : Light);
    }

    public static void Apply(string theme)
    {
        var dicts = Application.Current.Resources.MergedDictionaries;
        ResourceDictionary? light = null;
        ResourceDictionary? dark = null;
        foreach (var dict in dicts)
        {
            var src = dict.Source?.ToString() ?? "";
            if (src.EndsWith("Colors.Light.xaml", StringComparison.OrdinalIgnoreCase))
            {
                light = dict;
            }
            else if (src.EndsWith("Colors.Dark.xaml", StringComparison.OrdinalIgnoreCase))
            {
                dark = dict;
            }
        }

        if (light is null || dark is null)
        {
            return;
        }

        dicts.Remove(light);
        dicts.Remove(dark);
        if (theme == Dark)
        {
            dicts.Insert(0, light);
            dicts.Insert(1, dark);
        }
        else
        {
            dicts.Insert(0, dark);
            dicts.Insert(1, light);
        }

        Current = theme == Dark ? Dark : Light;
    }

    private static string SystemTheme()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(
                @"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize");
            if (key?.GetValue("AppsUseLightTheme") is int value)
            {
                return value == 0 ? Dark : Light;
            }
        }
        catch
        {
            // 读取失败时默认浅色
        }
        return Light;
    }
}
