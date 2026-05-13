import { COLORS } from '../../design/tokens';

interface EmptyStateProps {
  badge: string;
  title: string;
  description: string;
}

export function EmptyState({ badge, title, description }: EmptyStateProps) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '16px 12px',
      textAlign: 'center',
    }}>
      <div style={{
        width: 28,
        height: 28,
        borderRadius: 6,
        background: COLORS.bgSurface5,
        border: `1px solid ${COLORS.borderTertiary}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 13,
        fontWeight: 600,
        color: COLORS.textTertiary,
        marginBottom: 8,
        fontFamily: 'ui-monospace, monospace',
      }}>
        {badge}
      </div>
      <div style={{
        fontSize: 11,
        fontWeight: 500,
        color: COLORS.textSecondary,
        marginBottom: 3,
      }}>
        {title}
      </div>
      <div style={{
        fontSize: 10,
        color: COLORS.textTertiary,
        maxWidth: 170,
        lineHeight: 1.4,
      }}>
        {description}
      </div>
    </div>
  );
}
