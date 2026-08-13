using System.Net.Http;
using System.Net.Http.Json;
using DocTools.Models;

namespace DocTools.Services;

/// <summary>DocTools 本地 API 的 HTTP 客户端（REST + WebSocket 地址）。</summary>
public sealed class DocToolsApi
{
    private readonly HttpClient _http;

    public Uri BaseUrl { get; }

    public DocToolsApi(Uri baseUrl)
    {
        BaseUrl = baseUrl;
        _http = new HttpClient { BaseAddress = baseUrl, Timeout = TimeSpan.FromMinutes(5) };
    }

    public async Task<JobStatus> CreateJobAsync(JobRequest request, CancellationToken ct = default)
    {
        var resp = await _http.PostAsJsonAsync("jobs", request, ct);
        resp.EnsureSuccessStatusCode();
        return (await resp.Content.ReadFromJsonAsync<JobStatus>(ct))!;
    }

    public async Task<JobStatus> GetJobAsync(string jobId, CancellationToken ct = default)
    {
        return (await _http.GetFromJsonAsync<JobStatus>($"jobs/{jobId}", ct))!;
    }

    public async Task<Capabilities> GetCapabilitiesAsync(CancellationToken ct = default)
    {
        return (await _http.GetFromJsonAsync<Capabilities>("capabilities", ct))!;
    }

    /// <summary>拉取诊断报告原始 JSON（版本/平台/能力/环境变量）。</summary>
    public async Task<string> GetDiagnosticsJsonAsync(CancellationToken ct = default)
    {
        var resp = await _http.GetAsync("diagnostics", ct);
        resp.EnsureSuccessStatusCode();
        return await resp.Content.ReadAsStringAsync(ct);
    }

    public Uri JobWsUri(string jobId)
    {
        var path = BaseUrl.AbsolutePath.TrimEnd('/') + $"/jobs/{jobId}/ws";
        return new UriBuilder(BaseUrl) { Scheme = "ws", Path = path }.Uri;
    }
}
