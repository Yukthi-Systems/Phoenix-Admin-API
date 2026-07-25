# Quest DB Schema

This is Production DB and Table


Delete the Table DO NOT DO IT
```sql
DROP TABLE login_attempt;
```


Used to create the table
```sql
CREATE TABLE login_attempt (
  timestamp TIMESTAMP,
  origin_ip IPV4,
  email_id VARCHAR,
  domain_name SYMBOL CAPACITY 10000 NOCACHE
) TIMESTAMP (timestamp) 
PARTITION BY DAY
TTL 90d
WAL;
```


# Server Load Metrics Table

```json
{
  "server_id": "server-1.example.com",
  "cpu_percent": 4.57,
  "load_avg_1": 0,
  "load_avg_5": 0.02,
  "load_avg_15": 0.08,
  "mem_total_mb": 3819.19,
  "mem_used_mb": 1856.21,
  "mem_available_mb": 1638.64,
  "mem_percent": 48.6,
  "disk_total_gb": 37.24,
  "disk_used_gb": 5.82,
  "disk_free_gb": 29.87,
  "disk_percent": 16.3,
  "disk_read_MBps": 0,
  "disk_write_MBps": 0,
  "net_sent_MBps": 0,
  "net_recv_MBps": 0
}
```


```go
// ServerMetrics represents system metrics for a server
type ServerMetrics struct {
    ServerID        string  `json:"server_id"`
    CPUPercent      float64 `json:"cpu_percent"`
    LoadAvg1        float64 `json:"load_avg_1"`
    LoadAvg5        float64 `json:"load_avg_5"`
    LoadAvg15       float64 `json:"load_avg_15"`
    MemTotalMB      float64 `json:"mem_total_mb"`
    MemUsedMB       float64 `json:"mem_used_mb"`
    MemAvailableMB  float64 `json:"mem_available_mb"`
    MemPercent      float64 `json:"mem_percent"`
    DiskTotalGB     float64 `json:"disk_total_gb"`
    DiskUsedGB      float64 `json:"disk_used_gb"`
    DiskFreeGB      float64 `json:"disk_free_gb"`
    DiskPercent     float64 `json:"disk_percent"`
    DiskReadMBps    float64 `json:"disk_read_MBps"`
    DiskWriteMBps   float64 `json:"disk_write_MBps"`
    NetSentMBps     float64 `json:"net_sent_MBps"`
    NetRecvMBps     float64 `json:"net_recv_MBps"`
}
```

```rs
// ServerMetrics represents system metrics for a server by API
pub struct ServerMetrics {
    pub cpu_percent: f64,
    pub load_avg_1: f64,
    pub load_avg_5: f64,
    pub load_avg_15: f64,
    pub mem_total_mb: f64,
    pub mem_used_mb: f64,
    pub mem_available_mb: f64,
    pub mem_percent: f64,
    pub disk_total_gb: f64,
    pub disk_used_gb: f64,
    pub disk_free_gb: f64,
    pub disk_percent: f64,
    pub disk_read_mbps: f64,
    pub disk_write_mbps: f64,
    pub net_sent_mbps: f64,
    pub net_recv_mbps: f64,
}
```


- We will store 24 * 60 * 4 = 5760 records per day for each server (Every 15 Seconds)

- From around 15 Servers, we will have around 5760 * 15 = 86,400 records per day


```sql
CREATE TABLE server_metrics (
    timestamp TIMESTAMP,
    server_id SYMBOL,

    cpu_percent DOUBLE,
    
    load_avg_1 DOUBLE,
    load_avg_5 DOUBLE,
    load_avg_15 DOUBLE,

    mem_total_mb DOUBLE,
    mem_used_mb DOUBLE,
    mem_available_mb DOUBLE,
    mem_percent DOUBLE,

    disk_total_gb DOUBLE,
    disk_used_gb DOUBLE,
    disk_free_gb DOUBLE,
    disk_percent DOUBLE,

    disk_read_MBps DOUBLE,
    disk_write_MBps DOUBLE,

    net_sent_MBps DOUBLE,
    net_recv_MBps DOUBLE
) TIMESTAMP (timestamp)
PARTITION BY DAY
TTL 90d
WAL;
```
