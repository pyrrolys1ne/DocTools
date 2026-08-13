using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Text.Json.Serialization;

namespace DocTools.Models;

/// <summary>操作类型：批量表单 / 专用表单。</summary>
public enum OperationKind
{
    Batch,
    Merge,
    Split,
    PdfToImages,
}

/// <summary>
/// 操作定义（与后端 OPERATION_HANDLERS 对应的 12 个操作）。
/// RequiresEngine：该操作依赖的引擎名（与 /api/v1/capabilities 的 engines 键对应），
/// null 表示无依赖。IsAvailable 由 MainViewModel 加载 capabilities 后更新。
/// </summary>
public sealed class OperationDef : INotifyPropertyChanged
{
    public OperationDef(
        string id,
        string label,
        string[] exts,
        OperationKind kind,
        string group,
        string iconKey,
        string? requiresEngine = null)
    {
        Id = id;
        Label = label;
        Exts = exts;
        Kind = kind;
        Group = group;
        IconKey = iconKey;
        RequiresEngine = requiresEngine;
    }

    public string Id { get; }
    public string Label { get; }
    public string[] Exts { get; }
    public OperationKind Kind { get; }
    public string Group { get; }
    public string IconKey { get; }
    public string? RequiresEngine { get; }

    private bool _isAvailable = true;
    public bool IsAvailable
    {
        get => _isAvailable;
        set
        {
            if (_isAvailable == value)
            {
                return;
            }

            _isAvailable = value;
            OnPropertyChanged();
        }
    }

    private string? _unavailableReason;
    public string? UnavailableReason
    {
        get => _unavailableReason;
        set
        {
            _unavailableReason = value;
            OnPropertyChanged();
        }
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    private void OnPropertyChanged([CallerMemberName] string? name = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

/// <summary>POST /api/v1/jobs 请求体（字段名与后端 JobRequest 对齐）。</summary>
public sealed class JobRequest
{
    [JsonPropertyName("operation")] public string Operation { get; set; } = "";
    [JsonPropertyName("source_path")] public string SourcePath { get; set; } = "";
    [JsonPropertyName("output_path")] public string OutputPath { get; set; } = "";
    [JsonPropertyName("recursive")] public bool Recursive { get; set; }
    [JsonPropertyName("output_is_dir")] public bool OutputIsDir { get; set; }
    [JsonPropertyName("sources")] public List<string> Sources { get; set; } = new();
    [JsonPropertyName("page_ranges")] public string PageRanges { get; set; } = "";
    [JsonPropertyName("quality")] public int Quality { get; set; } = 80;
}

/// <summary>GET /api/v1/capabilities 响应（引擎可用性 + 资源预算）。</summary>
public sealed class Capabilities
{
    [JsonPropertyName("engines")] public Dictionary<string, bool> Engines { get; set; } = new();
    [JsonPropertyName("limits")] public Dictionary<string, int> Limits { get; set; } = new();
}

/// <summary>单个文件的处理结果。</summary>
public sealed class FileResult
{
    [JsonPropertyName("src")] public string Src { get; set; } = "";
    [JsonPropertyName("dst")] public string Dst { get; set; } = "";
    [JsonPropertyName("ok")] public bool Ok { get; set; }
    [JsonPropertyName("error")] public string? Error { get; set; }
    [JsonPropertyName("error_code")] public string? ErrorCode { get; set; }
    [JsonPropertyName("note")] public string? Note { get; set; }

    [JsonIgnore]
    public string OkText => Ok ? "OK" : "FAIL";

    [JsonIgnore]
    public string DisplayError => ErrorCode is null ? Error ?? "" : $"[{ErrorCode}] {Error}";

    [JsonIgnore]
    public string DisplayNote => Note ?? "";
}

/// <summary>任务状态快照（GET 与 WebSocket 推送共用同一结构）。</summary>
public sealed class JobStatus
{
    [JsonPropertyName("id")] public string Id { get; set; } = "";
    [JsonPropertyName("status")] public string Status { get; set; } = "";
    [JsonPropertyName("total")] public int Total { get; set; }
    [JsonPropertyName("done")] public int Done { get; set; }
    [JsonPropertyName("current")] public string? Current { get; set; }
    [JsonPropertyName("error")] public string? Error { get; set; }
    [JsonPropertyName("results")] public List<FileResult> Results { get; set; } = new();
}
