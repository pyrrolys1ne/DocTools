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
    private readonly DocServer _docServer;
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
    public ObservableCollection<string> ImageSources { get; } = new();

    public AppSettings Settings => _settings;

    public MainViewModel(DocToolsApi api, AppSettings settings, DocServer docServer)
    {
        _api = api;
        _docServer = docServer;
        _settings = settings;
        _mineruApiUrl = settings.MineruApiUrl;
        _mineruToken = settings.MineruToken;
        _ui = SynchronizationContext.Current
            ?? throw new InvalidOperationException("MainViewModel 必须在 UI 线程创建。");

        Operations = new List<OperationDef>
        {
            // PDF 类
            new("pdf-to-word", "PDF 转 Word", new[] { ".pdf" }, OperationKind.Batch, "PDF 转换", "Icon.PdfToWord", inputCategory: "pdf"),
            new("pdf-to-ppt", "PDF 转 PPT", new[] { ".pdf" }, OperationKind.Batch, "PDF 转换", "Icon.PdfToPpt", inputCategory: "pdf"),
            new("pdf-to-excel", "PDF 转 Excel", new[] { ".pdf" }, OperationKind.Batch, "PDF 转换", "Icon.PdfToWord", inputCategory: "pdf"),
            new("pdf-to-markdown", "PDF 解析（MinerU）", new[] { ".pdf" }, OperationKind.Batch, "PDF 转换", "Icon.PdfToWord", requiresEngine: "mineru", inputCategory: "pdf"),
            new("pdf-to-images", "PDF 转图片", new[] { ".pdf" }, OperationKind.PdfToImages, "PDF 转换", "Icon.PdfToImages", inputCategory: "pdf"),
            new("merge-pdf", "合并 PDF", new[] { ".pdf" }, OperationKind.Merge, "PDF 工具", "Icon.MergePdf", inputCategory: "pdf"),
            new("split-pdf", "拆分 PDF", new[] { ".pdf" }, OperationKind.Split, "PDF 工具", "Icon.SplitPdf", inputCategory: "pdf"),
            // Word 类
            new("word-to-pdf", "Word 转 PDF", new[] { ".docx", ".doc" }, OperationKind.Batch, "Office 转换", "Icon.WordToPdf", requiresEngine: "office", inputCategory: "word"),
            new("remove-headers", "去页眉", new[] { ".docx" }, OperationKind.Batch, "Word 清理", "Icon.RemoveHeaders", inputCategory: "word"),
            new("remove-footers", "去页脚", new[] { ".docx" }, OperationKind.Batch, "Word 清理", "Icon.RemoveFooters", inputCategory: "word"),
            new("remove-headers-footers", "去页眉页脚", new[] { ".docx" }, OperationKind.Batch, "Word 清理", "Icon.RemoveHeadersFooters", inputCategory: "word"),
            // 图片类
            new("image-to-pdf", "图片转 PDF", new[] { ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff" }, OperationKind.ImageMerge, "图片处理", "Icon.ImageToPdf", inputCategory: "image"),
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
        AddImageFilesCommand = new RelayCommand(AddImageFiles);
        MoveImageUpCommand = new RelayCommand(() => MoveImage(-1));
        MoveImageDownCommand = new RelayCommand(() => MoveImage(1));
        ExportDiagnosticsCommand = new RelayCommand(ExportDiagnostics);
        CheckUpdatesCommand = new RelayCommand(CheckForUpdates);
        SelectCategoryCommand = new RelayCommand<CategoryDef>(SelectCategory);
        SelectOperationCommand = new RelayCommand<OperationDef>(SelectOperation);
        BackCommand = new RelayCommand(GoBack);
        OpenSettingsCommand = new RelayCommand(OpenSettings);
    }

    // ---- MinerU 设置 ----

    private string _mineruApiUrl;
    private string _mineruToken;

    /// <summary>MinerU API 地址（自建 mineru-api，留空则默认官方 mineru.net）。</summary>
    public string MineruApiUrl
    {
        get => _mineruApiUrl;
        set { _mineruApiUrl = value; OnPropertyChanged(); }
    }

    /// <summary>MinerU Token（mineru.net 官方 Token，或自建服务的鉴权 Token）。</summary>
    public string MineruToken
    {
        get => _mineruToken;
        set { _mineruToken = value; OnPropertyChanged(); }
    }

    public RelayCommand OpenSettingsCommand { get; }

    private void OpenSettings()
    {
        var dialog = new Views.SettingsWindow { Owner = Application.Current.MainWindow };
        dialog.DataContext = this;
        dialog.ShowDialog();
    }

    /// <summary>保存 MinerU 配置并重启 docserver 使其生效（填 key 即可用）。</summary>
    public void SaveMineruSettings()
    {
        _settings.MineruApiUrl = MineruApiUrl.Trim();
        _settings.MineruToken = MineruToken.Trim();
        _settings.Save();

        try
        {
            var newUrl = _docServer.Restart(_settings);
            _api.UpdateBaseUrl(newUrl);
            _ = LoadCapabilitiesAsync();
            MessageBox.Show(
                "MinerU 配置已保存并生效，现在可以使用「PDF 解析（MinerU）」了。",
                "DocTools",
                MessageBoxButton.OK,
                MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                $"配置已保存，但重启本地服务失败：{ex.Message}\n请重启应用后生效。",
                "DocTools",
                MessageBoxButton.OK,
                MessageBoxImage.Warning);
        }
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
                    : op.RequiresEngine switch
                    {
                        "office" => "未检测到 Office 或 LibreOffice，此功能不可用。",
                        "mineru" => "未配置 MinerU API（DOCTOOLS_MINERU_API_URL），此功能不可用。",
                        _ => $"缺少引擎 {op.RequiresEngine}，此功能不可用。",
                    };
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
            OnPropertyChanged(nameof(IsImageMergeVisible));
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
        "pdf-to-markdown" => "MinerU 解析 PDF 为 Markdown（需配置 API）",
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

    public bool IsImageMergeVisible => SelectedOperation?.Kind == OperationKind.ImageMerge;

    /// <summary>图片转 PDF 队列当前选中项（上移/下移基于它）。</summary>
    public int SelectedImageIndex { get; set; } = -1;

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
    public RelayCommand AddImageFilesCommand { get; }
    public RelayCommand MoveImageUpCommand { get; }
    public RelayCommand MoveImageDownCommand { get; }
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

    private void AddImageFiles()
    {
        var dialog = new Microsoft.Win32.OpenFileDialog
        {
            Filter = "图片文件|*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp;*.tif;*.tiff",
            Multiselect = true,
        };
        if (dialog.ShowDialog() == true)
        {
            foreach (var file in dialog.FileNames)
            {
                ImageSources.Add(file);
            }
        }
    }

    private void MoveImage(int delta)
    {
        var index = SelectedImageIndex;
        if (index < 0 || index >= ImageSources.Count)
        {
            return;
        }

        var target = index + delta;
        if (target < 0 || target >= ImageSources.Count)
        {
            return;
        }

        ImageSources.Move(index, target);
        SelectedImageIndex = target;
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
            case OperationKind.ImageMerge:
                if (ImageSources.Count == 0)
                {
                    Error = "请至少添加一张图片";
                    return;
                }

                if (string.IsNullOrWhiteSpace(OutputPath))
                {
                    Error = "请选择输出 PDF 文件";
                    return;
                }

                request.Sources = ImageSources.ToList();
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
