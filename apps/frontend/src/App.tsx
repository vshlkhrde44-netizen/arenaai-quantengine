import React, { useState, useEffect, useRef } from 'react';
import { TopBar } from './components/TopBar';
import { Sidebar, NavTab } from './components/Sidebar';
import { DashboardScreen } from './screens/DashboardScreen';
import { MarketsScreen } from './screens/MarketsScreen';
import { MarketDataScreen } from './screens/MarketDataScreen';
import { MicrostructureScreen } from './screens/MicrostructureScreen';
import { StrategiesScreen } from './screens/StrategiesScreen';
import { ResearchScreen } from './screens/ResearchScreen';
import { BacktestingScreen } from './screens/BacktestingScreen';
import { WalkForwardScreen } from './screens/WalkForwardScreen';
import { StatisticalLabScreen } from './screens/StatisticalLabScreen';
import { DatasetsScreen } from './screens/DatasetsScreen';
import { PaperTradingScreen } from './screens/PaperTradingScreen';
import { OrdersScreen } from './screens/OrdersScreen';
import { PositionsScreen } from './screens/PositionsScreen';
import { PortfolioScreen } from './screens/PortfolioScreen';
import { RiskScreen } from './screens/RiskScreen';
import { AuditScreen } from './screens/AuditScreen';
import { ReportsScreen } from './screens/ReportsScreen';
import { SystemHealthScreen } from './screens/SystemHealthScreen';
import { SettingsScreen } from './screens/SettingsScreen';

import {
  TickerRecord,
  TradeRecord,
  PortfolioSummary,
  PaperOrder,
  PositionRecord,
  SystemHealth
} from './types';
import {
  fetchHealth,
  fetchPortfolioSummary,
  fetchTickers,
  fetchTrades,
  fetchOrders,
  fetchPositions
} from './api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [tickers, setTickers] = useState<Record<string, TickerRecord>>({});
  const [trades, setTrades] = useState<TradeRecord[]>([]);
  const [orders, setOrders] = useState<PaperOrder[]>([]);
  const [positions, setPositions] = useState<PositionRecord[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [feedLatencyMs, setFeedLatencyMs] = useState<number | null>(null);

  const wsRef = useRef<WebSocket | null>(null);

  // Poll baseline data
  const loadBaselineData = async () => {
    try {
      const [h, p, t, tr, o, pos] = await Promise.all([
        fetchHealth(),
        fetchPortfolioSummary(),
        fetchTickers(),
        fetchTrades('BTC-USD', 20),
        fetchOrders(),
        fetchPositions()
      ]);
      setHealth(h);
      setPortfolio(p);
      setTickers(t);
      setTrades(tr);
      setOrders(o);
      setPositions(pos);
      setIsConnected(h.market_data_feed.is_connected);
      setFeedLatencyMs(h.market_data_feed.feed_latency_ms);
    } catch (e) {
      console.error('Error fetching baseline data:', e);
    }
  };

  useEffect(() => {
    loadBaselineData();
    const interval = setInterval(loadBaselineData, 3000);
    return () => clearInterval(interval);
  }, []);

  // Connect WebSocket for high-frequency streaming
  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimeout: any;

    const connectWs = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/stream`;
      ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.tickers) {
            setTickers(data.tickers);
          }
          if (data.portfolio) {
            setPortfolio(data.portfolio);
          }
          if (data.recent_trades && data.recent_trades['BTC-USD']) {
            setTrades(data.recent_trades['BTC-USD']);
          }
          if (data.feed_health) {
            setFeedLatencyMs(data.feed_health.feed_latency_ms);
          }
        } catch (e) {
          console.error('WS parse error:', e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        reconnectTimeout = setTimeout(connectWs, 2000);
      };

      ws.onerror = () => {
        setIsConnected(false);
      };
    };

    connectWs();

    return () => {
      clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return (
    <div className="flex flex-col h-screen w-screen bg-[#07090e] text-slate-100 font-sans overflow-hidden">
      {/* Top Header Safety Bar */}
      <TopBar
        isConnected={isConnected}
        feedLatencyMs={feedLatencyMs}
        venue={health?.market_data_feed.venue ?? 'coinbase'}
        emergencyStopActive={health?.emergency_stop_active ?? false}
        onRefreshHealth={loadBaselineData}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Navigation Sidebar */}
        <Sidebar
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          openOrdersCount={portfolio?.open_orders_count ?? 0}
          activePositionsCount={portfolio?.active_positions_count ?? 0}
        />

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-5 bg-[#07090e]">
          {activeTab === 'dashboard' && (
            <DashboardScreen
              portfolio={portfolio}
              tickers={tickers}
              trades={trades}
              health={health}
              onNavigateTab={setActiveTab}
            />
          )}

          {activeTab === 'markets' && (
            <MarketsScreen tickers={tickers} trades={trades} />
          )}

          {activeTab === 'marketdata' && (
            <MarketDataScreen health={health} onRefresh={loadBaselineData} />
          )}

          {activeTab === 'microstructure' && (
            <MicrostructureScreen />
          )}

          {activeTab === 'strategies' && (
            <StrategiesScreen />
          )}

          {activeTab === 'research' && (
            <ResearchScreen />
          )}

          {activeTab === 'backtesting' && (
            <BacktestingScreen />
          )}

          {activeTab === 'walkforward' && (
            <WalkForwardScreen />
          )}

          {activeTab === 'statistical' && (
            <StatisticalLabScreen />
          )}

          {activeTab === 'datasets' && (
            <DatasetsScreen />
          )}

          {activeTab === 'papertrading' && (
            <PaperTradingScreen
              orders={orders}
              positions={positions}
              tickers={tickers}
              onRefreshOrders={loadBaselineData}
            />
          )}

          {activeTab === 'orders' && (
            <OrdersScreen orders={orders} />
          )}

          {activeTab === 'positions' && (
            <PositionsScreen positions={positions} />
          )}

          {activeTab === 'portfolio' && (
            <PortfolioScreen portfolio={portfolio} />
          )}

          {activeTab === 'risk' && (
            <RiskScreen />
          )}

          {activeTab === 'audit' && (
            <AuditScreen />
          )}

          {activeTab === 'reports' && (
            <ReportsScreen />
          )}

          {activeTab === 'systemhealth' && (
            <SystemHealthScreen health={health} onRefresh={loadBaselineData} />
          )}

          {activeTab === 'settings' && (
            <SettingsScreen />
          )}
        </main>
      </div>
    </div>
  );
};
