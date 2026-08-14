using System.Collections;
using System.Collections.ObjectModel;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

namespace DocTools.Behaviors;

/// <summary>
/// 让 ListBox 支持拖拽重排（上下拖动列表项调整顺序）。
/// 用法：&lt;ListBox behaviors:ListBoxReorderBehavior.EnableDragReorder="True" .../&gt;
/// 要求 ItemsSource 是可索引、可 Move 的集合（如 ObservableCollection&lt;string&gt;）。
/// </summary>
public static class ListBoxReorderBehavior
{
    private const string DragFormat = "DocTools.ReorderIndex";

    public static readonly DependencyProperty EnableDragReorderProperty =
        DependencyProperty.RegisterAttached(
            "EnableDragReorder",
            typeof(bool),
            typeof(ListBoxReorderBehavior),
            new PropertyMetadata(false, OnEnableDragReorderChanged));

    private static Point _startPoint;

    public static bool GetEnableDragReorder(DependencyObject obj)
        => (bool)obj.GetValue(EnableDragReorderProperty);

    public static void SetEnableDragReorder(DependencyObject obj, bool value)
        => obj.SetValue(EnableDragReorderProperty, value);

    private static void OnEnableDragReorderChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
    {
        if (d is not ListBox listBox)
        {
            return;
        }

        if ((bool)e.NewValue)
        {
            listBox.AllowDrop = true;
            listBox.PreviewMouseLeftButtonDown += OnPreviewMouseLeftButtonDown;
            listBox.PreviewMouseMove += OnPreviewMouseMove;
            listBox.Drop += OnDrop;
        }
        else
        {
            listBox.PreviewMouseLeftButtonDown -= OnPreviewMouseLeftButtonDown;
            listBox.PreviewMouseMove -= OnPreviewMouseMove;
            listBox.Drop -= OnDrop;
        }
    }

    private static void OnPreviewMouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        _startPoint = e.GetPosition(null);
    }

    private static void OnPreviewMouseMove(object sender, MouseEventArgs e)
    {
        if (e.LeftButton != MouseButtonState.Pressed)
        {
            return;
        }

        var position = e.GetPosition(null);
        if (Math.Abs(position.X - _startPoint.X) < SystemParameters.MinimumHorizontalDragDistance &&
            Math.Abs(position.Y - _startPoint.Y) < SystemParameters.MinimumVerticalDragDistance)
        {
            return;
        }

        if (sender is not ListBox listBox)
        {
            return;
        }

        var item = FindAncestor<ListBoxItem>((DependencyObject)e.OriginalSource);
        if (item is null)
        {
            return;
        }

        var items = listBox.ItemsSource as IList;
        if (items is null)
        {
            return;
        }

        var oldIndex = items.IndexOf(item.DataContext);
        if (oldIndex < 0)
        {
            return;
        }

        var data = new DataObject(DragFormat, oldIndex);
        DragDrop.DoDragDrop(listBox, data, DragDropEffects.Move);
    }

    private static void OnDrop(object sender, DragEventArgs e)
    {
        if (!e.Data.GetDataPresent(DragFormat) || sender is not ListBox listBox)
        {
            return;
        }

        var oldIndex = (int)e.Data.GetData(DragFormat)!;
        var target = FindAncestor<ListBoxItem>((DependencyObject)e.OriginalSource);
        if (target is null)
        {
            return;
        }

        var items = listBox.ItemsSource as IList;
        if (items is null)
        {
            return;
        }

        var newIndex = items.IndexOf(target.DataContext);
        if (newIndex < 0 || oldIndex == newIndex)
        {
            return;
        }

        if (items is ObservableCollection<string> collection)
        {
            collection.Move(oldIndex, newIndex);
        }
    }

    private static T? FindAncestor<T>(DependencyObject? obj) where T : DependencyObject
    {
        while (obj is not null)
        {
            if (obj is T typed)
            {
                return typed;
            }
            obj = VisualTreeHelper.GetParent(obj);
        }
        return null;
    }
}
