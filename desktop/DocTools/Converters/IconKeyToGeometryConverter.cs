using System.Globalization;
using System.Windows;
using System.Windows.Data;
using System.Windows.Media;

namespace DocTools.Converters;

/// <summary>把操作图标键（如 Icon.RemoveHeaders）解析为 Icons.xaml 里的 Geometry。</summary>
public sealed class IconKeyToGeometryConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        => Application.Current.TryFindResource(value) is Geometry geometry
            ? geometry
            : Binding.DoNothing;

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotSupportedException();
}
