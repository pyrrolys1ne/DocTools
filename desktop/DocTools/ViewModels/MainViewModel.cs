using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Data;
using DocTools.Models;
using DocTools.Services;

namespace DocTools.ViewModels;

public sealed class MainViewModel : INotifyPropertyChanged
{
    private readonly DocToolsApi _api;
    private readonly SynchronizationContext _ui;
    private readonly AppSettings _settings;
    private readonly UpdateService _updater = new();
    private JobWatcher? _watcher;
    private readonly HashSet<string> _seenResults = new();

    public IReadOnlyList<OperationDef> Operations { get; }
    public ICollectionView OperationsView { get; }
    public IReadOnlyList<CategoryDef> Categories { get; }
    public ObservableCollection<FileResult> Results { get; } = new();
    public ObservableCollection<string> MergeSources { get; } = new();

    public AppSettings Settings => _settings;

    public MainViewModel(DocToolsApi api, AppSettings settings)
    {
        _api = api;
        _settings = settings;
        _ui = SynchronizationContext.Current
            ?? throw new InvalidOperationException("MainViewModel 必须在 UI 线程创建。");

        Operations = new List<OperationDef>
        {
            // PDF 类
            new("pdf-to-word", "PDF 转 Word", new[] { ".pdf" }, OperationKind.Batch, "PDF 转换", "Icon.PdfToWord", inputCategory: "pdf"),
            new("pdf-to-ppt", "PDF 转 PPT", new[] { ".pdf" }, OperationKind.Batch, "PDF 转换", "Icon.PdfToPpt", inputCategory: "pdf"),
            new("pdf-to-excel", "PDF 转 Excel", new[] { ".pdf" }, OperationKind.Batch, "PDF 转换", "Icon.PdfToWord", inputCategory: "pdf"),
            new("pdf-to-images", "PDF 转图片", new[] { ".pdf" }, OperationKind.PdfToImages, "PDF 转换", "Icon.PdfToImages", inputCategory: "pdf"),
            new("merge-pdf", "合并 PDF", new[] { ".pdf" }, OperationKind.Merge, "PDF 工具", "Icon.MergePdf", inputCategory: "pdf"),
            new("split-pdf", "拆分 PDF", new[] { ".pdf" }, OperationKind.Split, "PDF 工具", "Icon.SplitPdf", inputCategory: "pdf"),
            // Word 类
            new("word-to-pdf", "Word 转 PDF", new[] { ".docx", ".doc" }, OperationKind.Batch, "Office 转换", "Icon.WordToPdf", requiresEngine: "office", inputCategory: "word"),
            new("remove-headers", "去页眉", new[] { ".docx" }, OperationKind.Batch, "Word 清理", "Icon.RemoveHeaders", inputCategory: "word"),
            new("remove-footers", "去页脚", new[] { ".docx" }, OperationKind.Batch, "Word 清理", "Icon.RemoveFooters", inputCategory: "word"),
            new("remove-headers-footers", "去页眉页脚", new[] { ".docx" }, OperationKind.Batch, "Word 清理", "Icon.RemoveHeadersFooters", inputCategory: "word"),
            // 图片类
            new("image-to-pdf", "图片转 PDF", new[] { ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff" }, OperationKind.Batch, "图片处理", "Icon.ImageToPdf", inputCategory: "image"),
            new("compress-images", "图片压缩", new[] { ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff" }, OperationKind.Batch, "图片处理", "Icon.CompressImages", inputCategory: "image"),
            new("convert-images", "图片格式互转", new[] { ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff" }, OperationKind.Batch, "图片处理", "Icon.CompressImages", inputCategory: "image"),
            // PPT 类
            new("ppt-to-pdf", "PPT 转 PDF", new[] { ".pptx", ".ppt" }, OperationKind.Batch, "Office 转换", "Icon.PptToPdf", requiresEngine: "office", inputCategory: "ppt"),
        };
        SelectedOperation = Operations[0];

        OperationsView = CollectionViewSource.GetDefaultView(Operations);
        OperationsView.GroupDescriptions.Add(new PropertyGroupDescription(nameof(OperationDef.Group)));

        Categories = new List<CategoryDef>
        {
            new("pdf", "PDF", "Icon.PdfToWord", "PDF 转 Word/PPT/Excel/图片，合并与拆分", Operations.Where(o => o.InputCategory == "pdf").ToList()),
            new("word", "Word", "Icon.WordToPdf", "Word 转 PDF，去页眉页脚", Operations.Where(o => o.InputCategory == "word").ToList()),
            new("image", "图片", "Icon.ImageToPdf", "图片转 PDF、压缩、格式互转", Operations.Where(o => o.InputCategory == "image").ToList()),
            new("ppt", "PPT", "Icon.PptToPdf", "PPT 转 PDF", Operations.Where(o => o.InputCategory == "ppt").ToList()),
        };

        Results.CollectionChanged += (_, _) => OnPropertyChanged(nameof(ResultsCardVisible));

        StartCommand = new RelayCommand(Start);
        BrowseFileCommand = new RelayCommand(BrowseFile);
        BrowseDirCommand = new RelayCommand(BrowseDir);
        BrowseOutputDirCommand = new RelayCommand(BrowseOutputDir);
        BrowseMergeOutputCommand = new RelayCommand(BrowseMergeOutput);
        AddMergeFilesCommand = new RelayCommand(AddMergeFiles);
        ExportDiagnosticsCommand = new RelayCommand(ExportDiagnostics);
        CheckUpdatesCommand = new RelayCommand(CheckForUpdates);
        SelectCategoryCommand = new RelayCommand<CategoryDef>(SelectCategory);
        SelectOperationCommand = new RelayCommand<OperationDef>(SelectOperation);
        BackCommand = new RelayCommand(GoBack);
    }

    // ---- 卡片式导航（主页 → 分类 → 操作）----

    private enum AppView { Home, Category, Operation }

    private AppView _currentView = AppView.Home;
    private CategoryDef? _currentCategory;

    public bool IsHomeVisible => _currentView == AppView.Home;
    public bool IsCategoryVisible => _currentView == AppView.Category;
    public bool IsOperationVisible => _currentView == AppView.Operation;
    public CategoryDef? CurrentCategory => _currentCategory;
    public string CurrentCategoryLabel => _currentCategory?.Label ?? "";
    public bool CanGoBack => _currentView != AppView.Home;

    public RelayCommand<CategoryDef> SelectCategoryCommand { get; }
    public RelayCommand<OperationDef> SelectOperationCommand { get; }
    public RelayCommand BackCommand { get; }

    private void SelectCategory(CategoryDef? category)
    {
        if (category is null)
        {
            return;
        }

        _currentCategory = category;
        _currentView = AppView.Category;
        NotifyNavigation();
    }

    private void SelectOperation(OperationDef? operation)
    {
        if (operation is null)
        {
            return;
        }

        SelectedOperation = operation;
        _currentView = AppView.Operation;
        NotifyNavigation();
    }

    private void GoBack()
    {
        _currentView = _currentView switch
        {
            AppView.Operation => AppView.Category,
            AppView.Category => AppView.Home,
            _ => AppView.Home,
        };
        NotifyNavigation();
    }

    public void GoHome()
    {
        _currentView = AppView.Home;
        _currentCategory = null;
        NotifyNavigation();
    }

    private void NotifyNavigation()
    {
        OnPropertyChanged(nameof(IsHomeVisible));
        OnPropertyChanged(nameof(IsCategoryVisible));
        OnPropertyChanged(nameof(IsOperationVisible));
        OnPropertyChanged(nameof(CurrentCategory));
        OnPropertyChanged(nameof(CurrentCategoryLabel));
        OnPropertyChanged(nameof(CanGoBack));
    }

    // ---- 引擎能力（/api/v1/capabilities）----

    /// <summary>拉取引擎能力清单并更新各操作的可用性（失败时保持默认可用，不打扰）。</summary>
    public async Task LoadCapabilitiesAsync()
    {
        try
        {
            var caps = await _api.GetCapabilitiesAsync();
            foreach (var op in Operations)
            {
                if (op.RequiresEngine is null)
                {
                    continue;
                }

                var available = caps.Engines.TryGetValue(op.RequiresEngine, out var ok) && ok;
                op.IsAvailable = available;
                op.UnavailableReason = available
                    ? null
                    : $"未检测到 Microsoft Office，{op.Label}不可用。请安装 Office 后重启。";
            }
        }
        catch (Exception ex)
        {
            // 能力探测失败不影响使用：所有操作保持可用，后端会给出明确错误
            System.Diagnostics.Debug.WriteLine($"LoadCapabilitiesAsync failed: {ex.Message}");
        }
    }

    // ---- 操作选择 ----

    private OperationDef? _selectedOperation;

    public OperationDef? SelectedOperation
    {
        get => _selectedOperation;
        set
        {
            if (Equals(_selectedOperation, value))
            {
                return;
            }

            _selectedOperation = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(SelectedOperationLabel));
            OnPropertyChanged(nameof(SelectedOperationHint));
            OnPropertyChanged(nameof(IsBatchVisible));
            OnPropertyChanged(nameof(IsMergeVisible));
            OnPropertyChanged(nameof(IsSplitVisible));
            OnPropertyChanged(nameof(IsPdfToImagesVisible));
            OnPropertyChanged(nameof(IsCompressVisible));
            OnPropertyChanged(nameof(IsConvertImagesVisible));
            ApplyRecents(value);
        }
    }

    public string SelectedOperationLabel => SelectedOperation?.Label ?? "选择一个操作";

    public string SelectedOperationHint => SelectedOperation?.Id switch
    {
        "remove-headers" => "批量去除 Word 文档页眉",
        "remove-footers" => "批量去除 Word 文档页脚",
        "remove-headers-footers" => "一次完成去页眉与页脚",
        "word-to-pdf" => "Word 转 PDF（Office 或 LibreOffice）",
        "ppt-to-pdf" => "PPT 转 PDF（Office 或 LibreOffice）",
        "image-to-pdf" => "目录内全部图片合成一个 PDF",
        "pdf-to-word" => "PDF 转 Word（扫描件自动 OCR）",
        "pdf-to-ppt" => "PDF 每页渲染为一张幻灯片",
        "pdf-to-excel" => "PDF 表格提取到 Excel（每表一个 sheet）",
        "pdf-to-images" => "PDF 每页导出一张 PNG",
        "compress-images" => "JPEG 重编码，其余格式转优化 PNG",
        "convert-images" => "图片格式互转（png/jpg/webp/bmp/gif/tiff）",
        "merge-pdf" => "按添加顺序合并多个 PDF",
        "split-pdf" => "按页或自定义范围拆分 PDF",
        _ => "",
    };

    public bool IsBatchVisible => SelectedOperation?.Kind == OperationKind.Batch;
    public bool IsMergeVisible => SelectedOperation?.Kind == OperationKind.Merge;
    public bool IsSplitVisible => SelectedOperation?.Kind == OperationKind.Split;
    public bool IsPdfToImagesVisible => SelectedOperation?.Kind == OperationKind.PdfToImages;
    public bool IsCompressVisible => SelectedOperation?.Id == "compress-images";

    // ---- 表单字段 ----

    private string _sourcePath = "";
    public string SourcePath
    {
        get => _sourcePath;
        set { _sourcePath = value; OnPropertyChanged(); }
    }

    private string _outputPath = "";
    public string OutputPath
    {
        get => _outputPath;
        set { _outputPath = value; OnPropertyChanged(); }
    }

    private bool _isRecursive;
    public bool IsRecursive
    {
        get => _isRecursive;
        set { _isRecursive = value; OnPropertyChanged(); }
    }

    private int _quality = 80;
    public int Quality
    {
        get => _quality;
        set { _quality = value; OnPropertyChanged(); }
    }

    private string _pageRanges = "";
    public string PageRanges
    {
        get => _pageRanges;
        set { _pageRanges = value; OnPropertyChanged(); }
    }

    private string _targetFormat = "png";
    public string TargetFormat
    {
        get => _targetFormat;
        set { _targetFormat = value; OnPropertyChanged(); }
    }

    public bool IsConvertImagesVisible => SelectedOperation?.Id == "convert-images";

    /// <summary>图片格式互转可选的目标格式。</summary>
    public IReadOnlyList<string> ImageTargetFormats { get; } = new[] { "png", "jpg", "webp", "bmp", "gif", "tiff" };

    // ---- 运行状态 ----

    private string _phase = "idle";
    public string Phase
    {
        get => _phase;
        set
        {
            _phase = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(NotBusy));
            OnPropertyChanged(nameof(IsRunningVisible));
            OnPropertyChanged(nameof(StatusText));
            OnPropertyChanged(nameof(ResultsCardVisible));
        }
    }

    public bool NotBusy => Phase != "running";
    public bool IsRunningVisible => Phase == "running";

    public string StatusText => Phase switch
    {
        "running" => "运行中…",
        "done" => "处理完成",
        "failed" => "处理失败",
        _ => "就绪",
    };

    private string _error = "";
    public string Error
    {
        get => _error;
        set
        {
            _error = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(HasError));
        }
    }

    private string _currentFile = "";
    public string CurrentFile
    {
        get => _currentFile;
        set { _currentFile = value; OnPropertyChanged(); }
    }

    private double _progress;
    public double Progress
    {
        get => _progress;
        set
        {
            _progress = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(ProgressPercent));
        }
    }

    public string ProgressPercent => $"{(int)Math.Round(Progress)}%";

    public int OkCount { get; private set; }
    public int FailCount { get; private set; }
    public string SummaryText => $"共 {Results.Count} 个结果，成功 {OkCount}，失败 {FailCount}";

    public bool HasError => !string.IsNullOrEmpty(Error);

    public bool ResultsCardVisible => Results.Count > 0 || Phase == "running";

    private void ApplyRecents(OperationDef? op)
    {
        if (op is null)
        {
            return;
        }

        SourcePath = _settings.Sources.TryGetValue(op.Id, out var source) ? source : "";
        OutputPath = _settings.Outputs.TryGetValue(op.Id, out var output) ? output : "";
    }

    // ---- 命令 ----

    public RelayCommand StartCommand { get; }
    public RelayCommand BrowseFileCommand { get; }
    public RelayCommand BrowseDirCommand { get; }
    public RelayCommand BrowseOutputDirCommand { get; }
    public RelayCommand BrowseMergeOutputCommand { get; }
    public RelayCommand AddMergeFilesCommand { get; }
    public RelayCommand ExportDiagnosticsCommand { get; }
    public RelayCommand CheckUpdatesCommand { get; }

    /// <summary>手动检查更新：有新版时询问下载安装；无更新或失败时给出明确提示。</summary>
    public async void CheckForUpdates()
    {
        try
        {
            var info = await _updater.CheckForUpdateAsync();
            if (info is null)
            {
                MessageBox.Show(
                    $"当前已是最新版本（v{_updater.CurrentVersion}）",
                    "检查更新",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);
                return;
            }

            var confirm = MessageBox.Show(
                $"发现新版本 v{info.Version}（当前 v{_updater.CurrentVersion}）。是否下载并安装？",
                "检查更新",
                MessageBoxButton.YesNo,
                MessageBoxImage.Question);
            if (confirm != MessageBoxResult.Yes)
            {
                return;
            }

            try
            {
                var cmdPath = await _updater.DownloadAndInstallAsync(info);
                Process.Start(new ProcessStartInfo
                {
                    FileName = cmdPath,
                    WindowStyle = ProcessWindowStyle.Hidden,
                    UseShellExecute = true,
                });
                Application.Current.Shutdown();
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    $"更新下载或校验失败：{ex.Message}",
                    "检查更新",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                $"检查更新失败：{ex.Message}",
                "检查更新",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
        }
    }

    /// <summary>启动时静默检查更新（受设置 CheckForUpdates 控制；失败不打扰）。</summary>
    public async Task CheckForUpdatesSilentlyAsync()
    {
        if (!_settings.CheckForUpdates)
        {
            return;
        }

        var info = await _updater.CheckForUpdateAsync();
        if (info is null)
        {
            return;
        }

        _ui.Post(_ =>
        {
            var confirm = MessageBox.Show(
                $"发现新版本 v{info.Version}（当前 v{_updater.CurrentVersion}）。是否现在更新？",
                "DocTools 更新",
                MessageBoxButton.YesNo,
                MessageBoxImage.Information);
            if (confirm == MessageBoxResult.Yes)
            {
                _ = InstallAsync(info);
            }
        }, null);
    }

    private async Task InstallAsync(UpdateInfo info)
    {
        try
        {
            var cmdPath = await _updater.DownloadAndInstallAsync(info);
            Process.Start(new ProcessStartInfo
            {
                FileName = cmdPath,
                WindowStyle = ProcessWindowStyle.Hidden,
                UseShellExecute = true,
            });
            Application.Current.Shutdown();
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                $"更新下载或校验失败：{ex.Message}",
                "DocTools 更新",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
        }
    }

    /// <summary>导出诊断报告：拉取 /api/v1/diagnostics 并保存为 JSON 文件。</summary>
    public async void ExportDiagnostics()
    {
        try
        {
            var json = await _api.GetDiagnosticsJsonAsync();
            var dialog = new Microsoft.Win32.SaveFileDialog
            {
                FileName = $"DocTools-diagnostics-{DateTime.Now:yyyyMMdd-HHmmss}.json",
                Filter = "JSON 文件|*.json",
                DefaultExt = ".json",
            };
            if (dialog.ShowDialog() != true)
            {
                return;
            }

            await File.WriteAllTextAsync(dialog.FileName, json);
            MessageBox.Show(
                $"诊断报告已保存到：{dialog.FileName}",
                "DocTools",
                MessageBoxButton.OK,
                MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                $"导出诊断报告失败：{ex.Message}",
                "DocTools",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
        }
    }

    private void BrowseFile()
    {
        var dialog = new Microsoft.Win32.OpenFileDialog { Filter = BuildFilter(SelectedOperation) };
        if (dialog.ShowDialog() == true)
        {
            SourcePath = dialog.FileName;
        }
    }

    private void BrowseDir()
    {
        var dialog = new Microsoft.Win32.OpenFolderDialog { Title = "选择源目录" };
        if (dialog.ShowDialog() == true)
        {
            SourcePath = dialog.FolderName;
        }
    }

    private void BrowseOutputDir()
    {
        var dialog = new Microsoft.Win32.OpenFolderDialog { Title = "选择输出目录" };
        if (dialog.ShowDialog() == true)
        {
            OutputPath = dialog.FolderName;
        }
    }

    private void BrowseMergeOutput()
    {
        var dialog = new Microsoft.Win32.SaveFileDialog
        {
            FileName = "merged.pdf",
            Filter = "PDF 文件|*.pdf",
        };
        if (dialog.ShowDialog() == true)
        {
            OutputPath = dialog.FileName;
        }
    }

    private void AddMergeFiles()
    {
        var dialog = new Microsoft.Win32.OpenFileDialog
        {
            Filter = "PDF 文件|*.pdf",
            Multiselect = true,
        };
        if (dialog.ShowDialog() == true)
        {
            foreach (var file in dialog.FileNames)
            {
                MergeSources.Add(file);
            }
        }
    }

    private static string BuildFilter(OperationDef? operation)
    {
        if (operation is null || operation.Exts.Length == 0)
        {
            return "所有文件|*.*";
        }

        var pattern = string.Join(";", operation.Exts);
        return $"{pattern} 文件|{pattern}|所有文件|*.*";
    }

    private async void Start()
    {
        var operation = SelectedOperation;
        if (operation is null)
        {
            return;
        }

        if (!operation.IsAvailable)
        {
            Error = operation.UnavailableReason ?? $"当前环境不支持 {operation.Label}";
            return;
        }

        Error = "";
        var request = new JobRequest { Operation = operation.Id };
        switch (operation.Kind)
        {
            case OperationKind.Batch:
                if (string.IsNullOrWhiteSpace(SourcePath))
                {
                    Error = "请填写源路径";
                    return;
                }

                request.SourcePath = SourcePath.Trim();
                request.OutputPath = OutputPath.Trim();
                request.Recursive = IsRecursive;
                request.Quality = Quality;
                request.TargetFormat = TargetFormat;
                break;
            case OperationKind.Merge:
                if (MergeSources.Count == 0)
                {
                    Error = "请至少添加一个 PDF 文件";
                    return;
                }

                request.Sources = MergeSources.ToList();
                request.OutputPath = OutputPath.Trim();
                break;
            case OperationKind.Split:
                if (string.IsNullOrWhiteSpace(SourcePath))
                {
                    Error = "请选择源 PDF 文件";
                    return;
                }

                request.SourcePath = SourcePath.Trim();
                request.OutputPath = OutputPath.Trim();
                request.PageRanges = PageRanges.Trim();
                break;
            case OperationKind.PdfToImages:
                if (string.IsNullOrWhiteSpace(SourcePath))
                {
                    Error = "请选择源 PDF 文件";
                    return;
                }

                request.SourcePath = SourcePath.Trim();
                request.OutputPath = OutputPath.Trim();
                break;
        }

        _settings.Sources[operation.Id] = SourcePath.Trim();
        _settings.Outputs[operation.Id] = OutputPath.Trim();
        _settings.Save();

        Results.Clear();
        _seenResults.Clear();
        OkCount = 0;
        FailCount = 0;
        CurrentFile = "";
        Progress = 0;
        Phase = "running";

        try
        {
            var job = await _api.CreateJobAsync(request);
            _watcher?.Dispose();
            _watcher = new JobWatcher(_api, job.Id);
            _watcher.Updated += OnJobUpdated;
            _watcher.Start();
        }
        catch (Exception ex)
        {
            Phase = "idle";
            Error = $"创建任务失败：{ex.Message}";
        }
    }

    private void OnJobUpdated(JobStatus status) => _ui.Post(_ => ApplyStatus(status), null);

    private void ApplyStatus(JobStatus status)
    {
        Progress = status.Total > 0 ? (double)status.Done / status.Total * 100 : 0;
        CurrentFile = status.Current ?? "";

        foreach (var result in status.Results)
        {
            var key = result.Src + "\u0001" + result.Dst;
            if (_seenResults.Add(key))
            {
                Results.Add(result);
            }
        }

        OkCount = Results.Count(r => r.Ok);
        FailCount = Results.Count - OkCount;
        OnPropertyChanged(nameof(SummaryText));

        if (status.Status is "done" or "failed")
        {
            _watcher?.Dispose();
            _watcher = null;
            Phase = status.Status;
            if (status.Status == "failed")
            {
                Error = status.Error ?? "处理失败";
            }
        }
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    private void OnPropertyChanged([CallerMemberName] string? name = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}
