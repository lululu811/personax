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

-- daily_basic: daily valuation metrics
CREATE TABLE IF NOT EXISTS daily_basic (
    code VARCHAR(20),
    trade_date DATE,
    close DECIMAL(12,4),
    turnover_rate DECIMAL(8,4),
    turnover_rate_f DECIMAL(8,4),
    volume_ratio DECIMAL(8,4),
    pe DECIMAL(12,4),
    pe_ttm DECIMAL(12,4),
    pb DECIMAL(12,4),
    ps DECIMAL(12,4),
    ps_ttm DECIMAL(12,4),
    dv_ratio DECIMAL(8,4),
    dv_ttm DECIMAL(8,4),
    total_share DECIMAL(20,4),
    float_share DECIMAL(20,4),
    free_share DECIMAL(20,4),
    total_mv DECIMAL(20,4),
    circ_mv DECIMAL(20,4),
    source VARCHAR(20),
    PRIMARY KEY (code, trade_date)
);

-- income: profit statement (quarterly)
CREATE TABLE IF NOT EXISTS income (
    code VARCHAR(20),
    report_date DATE,
    report_type VARCHAR(10),
    revenue DECIMAL(20,4),
    operating_cost DECIMAL(20,4),
    operating_profit DECIMAL(20,4),
    total_profit DECIMAL(20,4),
    net_profit DECIMAL(20,4),
    net_profit_dedt DECIMAL(20,4),
    basic_eps DECIMAL(12,4),
    diluted_eps DECIMAL(12,4),
    gross_profit DECIMAL(20,4),
    finance_cost DECIMAL(20,4),
    income_tax DECIMAL(20,4),
    rd_expense DECIMAL(20,4),
    total_compr_income DECIMAL(20,4),
    source VARCHAR(20),
    PRIMARY KEY (code, report_date, report_type)
);

-- balancesheet: balance sheet (quarterly)
CREATE TABLE IF NOT EXISTS balancesheet (
    code VARCHAR(20),
    report_date DATE,
    report_type VARCHAR(10),
    total_assets DECIMAL(20,4),
    total_liab DECIMAL(20,4),
    total_equity DECIMAL(20,4),
    total_cur_assets DECIMAL(20,4),
    total_cur_liab DECIMAL(20,4),
    money_cap DECIMAL(20,4),
    trad_asset DECIMAL(20,4),
    inventories DECIMAL(20,4),
    fix_assets DECIMAL(20,4),
    intan_assets DECIMAL(20,4),
    goodwill DECIMAL(20,4),
    total_nca DECIMAL(20,4),
    total_ncl DECIMAL(20,4),
    notes_receiv DECIMAL(20,4),
    accounts_receiv DECIMAL(20,4),
    source VARCHAR(20),
    PRIMARY KEY (code, report_date, report_type)
);

-- cashflow: cash flow statement (quarterly)
CREATE TABLE IF NOT EXISTS cashflow (
    code VARCHAR(20),
    report_date DATE,
    report_type VARCHAR(10),
    net_operate_cash_flow DECIMAL(20,4),
    net_invest_cash_flow DECIMAL(20,4),
    net_finance_cash_flow DECIMAL(20,4),
    cash_equ_end_period DECIMAL(20,4),
    sales_service_cash DECIMAL(20,4),
    buy_service_cash DECIMAL(20,4),
    employ_cash DECIMAL(20,4),
    tax_pay_cash DECIMAL(20,4),
    c_fr_sg DECIMAL(20,4),
    c_inf_fr_operate DECIMAL(20,4),
    c_paid_for_debt DECIMAL(20,4),
    c_paid_to_for_empl DECIMAL(20,4),
    source VARCHAR(20),
    PRIMARY KEY (code, report_date, report_type)
);

-- fina_indicator: financial indicators (quarterly, core fields)
CREATE TABLE IF NOT EXISTS fina_indicator (
    code VARCHAR(20),
    report_date DATE,
    report_type VARCHAR(10),
    eps DECIMAL(12,4),
    dt_eps DECIMAL(12,4),
    bps DECIMAL(12,4),
    roe DECIMAL(8,4),
    roe_waa DECIMAL(8,4),
    roe_dt DECIMAL(8,4),
    roa DECIMAL(8,4),
    roic DECIMAL(8,4),
    grossprofit_margin DECIMAL(8,4),
    netprofit_margin DECIMAL(8,4),
    debt_to_assets DECIMAL(8,4),
    current_ratio DECIMAL(8,4),
    quick_ratio DECIMAL(8,4),
    ocf_to_or DECIMAL(8,4),
    salescash_to_or DECIMAL(8,4),
    basic_eps_yoy DECIMAL(8,4),
    netprofit_yoy DECIMAL(8,4),
    dt_netprofit_yoy DECIMAL(8,4),
    tr_yoy DECIMAL(8,4),
    or_yoy DECIMAL(8,4),
    rd_exp DECIMAL(20,4),
    q_netprofit_yoy DECIMAL(8,4),
    q_roe DECIMAL(8,4),
    q_grossprofit_margin DECIMAL(8,4),
    q_netprofit_margin DECIMAL(8,4),
    source VARCHAR(20),
    PRIMARY KEY (code, report_date, report_type)
);

-- adj_factor: adjustment factor for price restoration
CREATE TABLE IF NOT EXISTS adj_factor (
    code VARCHAR(20),
    trade_date DATE,
    adj_factor DECIMAL(20,8),
    source VARCHAR(20),
    PRIMARY KEY (code, trade_date)
);

-- watchlist: user's watchlist stocks
CREATE TABLE IF NOT EXISTS watchlist (
    code VARCHAR(20) NOT NULL,
    name VARCHAR(100),
    added_at TIMESTAMP DEFAULT now(),
    category VARCHAR(50) DEFAULT 'default',
    status VARCHAR(20) DEFAULT 'active',
    notes TEXT,
    persona_name VARCHAR(50) DEFAULT 'zettaranc',
    PRIMARY KEY (code, persona_name)
);

-- holdings: user's current holdings
CREATE TABLE IF NOT EXISTS holdings (
    code VARCHAR(20) NOT NULL,
    name VARCHAR(100),
    shares DECIMAL(20,4) DEFAULT 0,
    avg_cost DECIMAL(12,4),
    current_price DECIMAL(12,4),
    market_value DECIMAL(20,4),
    pl_amount DECIMAL(20,4),
    pl_ratio DECIMAL(8,4),
    weight DECIMAL(8,4),
    sector VARCHAR(50),
    status VARCHAR(20) DEFAULT 'holding',
    notes TEXT,
    updated_at TIMESTAMP DEFAULT now(),
    persona_name VARCHAR(50) DEFAULT 'zettaranc',
    PRIMARY KEY (code, persona_name)
);

-- trades: user's trade records (delivery orders)
CREATE TABLE IF NOT EXISTS trades (
    trade_date DATE NOT NULL,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(100),
    trade_type VARCHAR(10) NOT NULL,
    shares DECIMAL(20,4) NOT NULL,
    price DECIMAL(12,4) NOT NULL,
    amount DECIMAL(20,4),
    fee DECIMAL(12,4) DEFAULT 0,
    tax DECIMAL(12,4) DEFAULT 0,
    total_cost DECIMAL(20,4),
    status VARCHAR(20) DEFAULT 'confirmed',
    notes TEXT,
    persona_name VARCHAR(50) DEFAULT 'zettaranc',
    created_at TIMESTAMP DEFAULT now()
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
