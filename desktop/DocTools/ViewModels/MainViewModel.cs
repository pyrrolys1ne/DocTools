using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using DocTools.Models;
using DocTools.Services;

namespace DocTools.ViewModels;

public sealed class MainViewModel : INotifyPropertyChanged
{
    private readonly DocToolsApi _api;
    private readonly SynchronizationContext _ui;
    private JobWatcher? _watcher;
    private readonly HashSet<string> _seenResults = new();

    public IReadOnlyList<OperationDef> Operations { get; }
    public ObservableCollection<FileResult> Results { get; } = new();
    public ObservableCollection<string> MergeSources { get; } = new();

    public MainViewModel(DocToolsApi api)
    {
        _api = api;
        _ui = SynchronizationContext.Current
            ?? throw new InvalidOperationException("MainViewModel 必须在 UI 线程创建。");

        Operations = new List<OperationDef>
        {
            new("remove-headers", "去页眉", new[] { ".docx" }, OperationKind.Batch),
            new("remove-footers", "去页脚", new[] { ".docx" }, OperationKind.Batch),
            new("remove-headers-footers", "去页眉页脚", new[] { ".docx" }, OperationKind.Batch),
            new("word-to-pdf", "Word 转 PDF", new[] { ".docx", ".doc" }, OperationKind.Batch),
            new("ppt-to-pdf", "PPT 转 PDF", new[] { ".pptx", ".ppt" }, OperationKind.Batch),
            new("image-to-pdf", "图片转 PDF", new[] { ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff" }, OperationKind.Batch),
            new("pdf-to-word", "PDF 转 Word", new[] { ".pdf" }, OperationKind.Batch),
            new("pdf-to-ppt", "PDF 转 PPT", new[] { ".pdf" }, OperationKind.Batch),
            new("compress-images", "图片压缩", new[] { ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff" }, OperationKind.Batch),
            new("pdf-to-images", "PDF 转图片", new[] { ".pdf" }, OperationKind.PdfToImages),
            new("merge-pdf", "合并 PDF", new[] { ".pdf" }, OperationKind.Merge),
            new("split-pdf", "拆分 PDF", new[] { ".pdf" }, OperationKind.Split),
        };
        SelectedOperation = Operations[0];

        StartCommand = new RelayCommand(Start);
        BrowseFileCommand = new RelayCommand(BrowseFile);
        BrowseDirCommand = new RelayCommand(BrowseDir);
        BrowseOutputDirCommand = new RelayCommand(BrowseOutputDir);
        BrowseMergeOutputCommand = new RelayCommand(BrowseMergeOutput);
        AddMergeFilesCommand = new RelayCommand(AddMergeFiles);
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
        }
    }

    public string SelectedOperationLabel => SelectedOperation?.Label ?? "选择一个操作";

    public string SelectedOperationHint => SelectedOperation?.Id switch
    {
        "remove-headers" => "批量去除 Word 文档页眉",
        "remove-footers" => "批量去除 Word 文档页脚",
        "remove-headers-footers" => "一次完成去页眉与页脚",
        "word-to-pdf" => "Word 转 PDF（需本机安装 Microsoft Office）",
        "ppt-to-pdf" => "PPT 转 PDF（需本机安装 Microsoft Office）",
        "image-to-pdf" => "目录内全部图片合成一个 PDF",
        "pdf-to-word" => "PDF 转 Word（有损转换，扫描件效果有限）",
        "pdf-to-ppt" => "PDF 每页渲染为一张幻灯片",
        "compress-images" => "JPEG 重编码，其余格式转优化 PNG",
        "pdf-to-images" => "PDF 每页导出一张 PNG",
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

    private bool _isDryRun;
    public bool IsDryRun
    {
        get => _isDryRun;
        set { _isDryRun = value; OnPropertyChanged(); }
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
        set { _error = value; OnPropertyChanged(); }
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
        set { _progress = value; OnPropertyChanged(); }
    }

    public int OkCount { get; private set; }
    public int FailCount { get; private set; }
    public string SummaryText => $"共 {Results.Count} 个结果，成功 {OkCount}，失败 {FailCount}";

    // ---- 命令 ----

    public RelayCommand StartCommand { get; }
    public RelayCommand BrowseFileCommand { get; }
    public RelayCommand BrowseDirCommand { get; }
    public RelayCommand BrowseOutputDirCommand { get; }
    public RelayCommand BrowseMergeOutputCommand { get; }
    public RelayCommand AddMergeFilesCommand { get; }

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
                request.DryRun = IsDryRun;
                request.Quality = Quality;
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