-- stocks: basic stock information
CREATE TABLE IF NOT EXISTS stocks (
    code VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    industry VARCHAR(50),
    market VARCHAR(10),
    list_date DATE,
    is_active BOOLEAN DEFAULT true
);

-- daily_prices: daily OHLCV data (core table)
CREATE TABLE IF NOT EXISTS daily_prices (
    code VARCHAR(20),
    trade_date DATE,
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4),
    volume BIGINT,
    amount DECIMAL(20,4),
    change_pct DECIMAL(8,4),
    turnover_rate DECIMAL(8,4),
    source VARCHAR(20),
    created_at TIMESTAMP DEFAULT now(),
    PRIMARY KEY (code, trade_date)
);

-- fund_flow: capital flow data
CREATE TABLE IF NOT EXISTS fund_flow (
    code VARCHAR(20),
    trade_date DATE,
    main_in DECIMAL(20,4),
    main_out DECIMAL(20,4),
    main_net DECIMAL(20,4),
    retail_in DECIMAL(20,4),
    retail_out DECIMAL(20,4),
    retail_net DECIMAL(20,4),
    total_amount DECIMAL(20,4),
    source VARCHAR(20),
    PRIMARY KEY (code, trade_date)
);

-- financials: financial report data
CREATE TABLE IF NOT EXISTS financials (
    code VARCHAR(20),
    report_date DATE,
    report_type VARCHAR(10),
    eps DECIMAL(12,4),
    bvps DECIMAL(12,4),
    pe DECIMAL(12,4),
    pb DECIMAL(12,4),
    roe DECIMAL(8,4),
    revenue DECIMAL(20,4),
    net_profit DECIMAL(20,4),
    source VARCHAR(20),
    PRIMARY KEY (code, report_date, report_type)
);

-- sync_log: data synchronization log
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY,
    table_name VARCHAR(50),
    code VARCHAR(20),
    data_source VARCHAR(20),
    start_date DATE,
    end_date DATE,
    records_count INTEGER,
    status VARCHAR(20),
    error_msg VARCHAR(500),
    synced_at TIMESTAMP DEFAULT now()
);
