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

/// <summary>操作定义（与后端 OPERATION_HANDLERS 对应的 12 个操作）。</summary>
public sealed record OperationDef(string Id, string Label, string[] Exts, OperationKind Kind);

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

/// <summary>单个文件的处理结果。</summary>
public sealed class FileResult
{
    [JsonPropertyName("src")] public string Src { get; set; } = "";
    [JsonPropertyName("dst")] public string Dst { get; set; } = "";
    [JsonPropertyName("ok")] public bool Ok { get; set; }
    [JsonPropertyName("error")] public string? Error { get; set; }

    [JsonIgnore]
    public string OkText => Ok ? "OK" : "FAIL";
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
