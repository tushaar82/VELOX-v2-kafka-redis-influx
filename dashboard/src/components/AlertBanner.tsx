/**
 * Alert Banner - Shows system notifications
 */
import React, { useEffect } from 'react';
import { X, AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';
import { useDashboardStore } from '../store/dashboardStore';

export const AlertBanner: React.FC = () => {
  const { alerts, removeAlert } = useDashboardStore();

  useEffect(() => {
    // Auto-remove alerts after 5 seconds
    const timers = alerts.map((alert) =>
      setTimeout(() => removeAlert(alert.id), 5000)
    );

    return () => {
      timers.forEach(clearTimeout);
    };
  }, [alerts, removeAlert]);

  if (alerts.length === 0) return null;

  const getIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle size={20} />;
      case 'error':
        return <AlertCircle size={20} />;
      case 'warning':
        return <AlertTriangle size={20} />;
      default:
        return <Info size={20} />;
    }
  };

  const getStyles = (type: string) => {
    switch (type) {
      case 'success':
        return 'bg-success-50 text-success-800 border-success-500';
      case 'error':
        return 'bg-danger-50 text-danger-800 border-danger-500';
      case 'warning':
        return 'bg-yellow-50 text-yellow-800 border-yellow-500';
      default:
        return 'bg-primary-50 text-primary-800 border-primary-500';
    }
  };

  return (
    <div className="fixed top-20 right-6 z-50 space-y-2 max-w-md">
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={`flex items-center gap-3 p-4 rounded-lg border-l-4 shadow-lg ${getStyles(alert.type)} animate-slide-in`}
        >
          <div className="flex-shrink-0">{getIcon(alert.type)}</div>
          <div className="flex-1">
            <p className="text-sm font-medium">{alert.message}</p>
          </div>
          <button
            onClick={() => removeAlert(alert.id)}
            className="flex-shrink-0 hover:opacity-70 transition-opacity"
          >
            <X size={18} />
          </button>
        </div>
      ))}
    </div>
  );
};
