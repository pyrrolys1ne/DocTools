using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using DocTools.Models;

namespace DocTools.Services;

/// <summary>
/// 订阅任务进度：优先 WebSocket 实时推送，失败时回退到固定间隔轮询。
/// 事件在后台线程触发，调用方需自行切回 UI 线程。
/// </summary>
public sealed class JobWatcher : IDisposable
{
    private readonly DocToolsApi _api;
    private readonly string _jobId;
    private readonly CancellationTokenSource _cts = new();

    public event Action<JobStatus>? Updated;

    public JobWatcher(DocToolsApi api, string jobId)
    {
        _api = api;
        _jobId = jobId;
    }

    public void Start() => _ = RunAsync(_cts.Token);

    private async Task RunAsync(CancellationToken ct)
    {
        var finished = false;

        try
        {
            using var ws = new ClientWebSocket();
            await ws.ConnectAsync(_api.JobWsUri(_jobId), ct);
            var buffer = new byte[64 * 1024];
            while (ws.State == WebSocketState.Open && !ct.IsCancellationRequested)
            {
                using var ms = new MemoryStream();
                WebSocketReceiveResult result;
                do
                {
                    result = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), ct);
                    ms.Write(buffer, 0, result.Count);
                }
                while (!result.EndOfMessage && ws.State == WebSocketState.Open);

                var status = JsonSerializer.Deserialize<JobStatus>(
                    Encoding.UTF8.GetString(ms.ToArray()));
                if (status is null)
                {
                    continue;
                }

                Updated?.Invoke(status);
                if (status.Status is "done" or "failed")
                {
                    finished = true;
                    break;
                }
            }
        }
        catch (OperationCanceledException)
        {
            return;
        }
        catch
        {
            // WebSocket 不可用，回退到轮询。
        }

        if (finished)
        {
            return;
        }

        while (!ct.IsCancellationRequested)
        {
            try
            {
                var status = await _api.GetJobAsync(_jobId, ct);
                Updated?.Invoke(status);
                if (status.Status is "done" or "failed")
                {
                    return;
                }
            }
            catch (OperationCanceledException)
            {
                return;
            }
            catch
            {
                // 服务短暂不可用时继续重试。
            }

            try
            {
                await Task.Delay(500, ct);
            }
            catch (OperationCanceledException)
            {
                return;
            }
        }
    }

    public void Dispose()
    {
        _cts.Cancel();
        _cts.Dispose();
    }
}