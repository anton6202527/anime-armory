import { Check, Crown, Diamond, ShieldCheck, Sparkles, X, Zap } from "lucide-react";
import { useEffect, useState } from "react";

type BillingTab = "membership" | "credits";

const MEMBERSHIP_PLANS = [
  { id: "month", name: "月度会员", price: "¥29", unit: "/ 月", credits: "每月 1,200 积分", tag: "轻量创作" },
  { id: "year", name: "年度会员", price: "¥239", unit: "/ 年", credits: "每年 18,000 积分", tag: "限时 4 折", recommended: true },
  { id: "studio", name: "创作会员", price: "¥59", unit: "/ 月", credits: "每月 4,000 积分", tag: "高频生成" },
] as const;

const CREDIT_PACKAGES = [
  { id: "credits-500", amount: "500", price: "¥10", gift: "" },
  { id: "credits-1200", amount: "1,200", price: "¥20", gift: "多送 200" },
  { id: "credits-3000", amount: "3,000", price: "¥45", gift: "多送 750", recommended: true },
  { id: "credits-8000", amount: "8,000", price: "¥108", gift: "多送 2,600" },
] as const;

export function MembershipDialog({
  open,
  onClose,
  onPurchase,
}: {
  open: boolean;
  onClose: () => void;
  onPurchase: (label: string) => void;
}) {
  const [tab, setTab] = useState<BillingTab>("membership");
  const [membershipId, setMembershipId] = useState("year");
  const [creditsId, setCreditsId] = useState("credits-3000");

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, open]);

  if (!open) return null;

  const membership = MEMBERSHIP_PLANS.find((plan) => plan.id === membershipId) ?? MEMBERSHIP_PLANS[1];
  const credits = CREDIT_PACKAGES.find((item) => item.id === creditsId) ?? CREDIT_PACKAGES[2];
  const purchaseLabel = tab === "membership" ? membership.name : `${credits.amount} 积分`;

  return (
    <div className="membership-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="membership-dialog" role="dialog" aria-modal="true" aria-labelledby="membership-title" onMouseDown={(event) => event.stopPropagation()}>
        <button className="membership-close" type="button" onClick={onClose} aria-label="关闭会员与积分窗口"><X size={16} /></button>

        <header className="membership-header">
          <div className="membership-title">
            <span><Crown size={20} /></span>
            <div><h2 id="membership-title">会员与积分</h2><small>为全模态创作补充更多生成额度</small></div>
          </div>
          <div className="membership-balance"><span><Zap size={13} fill="currentColor" />积分余额</span><strong>20</strong></div>
        </header>

        <nav className="membership-tabs" aria-label="购买类型">
          <button className={tab === "membership" ? "active" : ""} type="button" onClick={() => setTab("membership")}><Crown size={15} />会员套餐</button>
          <button className={tab === "credits" ? "active" : ""} type="button" onClick={() => setTab("credits")}><Zap size={15} />积分充值</button>
        </nav>

        <div className="membership-body">
          {tab === "membership" ? (
            <>
              <section className="membership-hero">
                <div><span className="membership-vip-mark"><Diamond size={14} fill="currentColor" />VIP</span><h3>解锁高阶模型，创作更尽兴</h3><p>会员积分按月发放，可用于图片、视频、音频及高阶文本模型。</p></div>
                <ul><li><Check size={13} />高阶模型优先使用</li><li><Check size={13} />每月会员积分</li><li><Check size={13} />生成任务优先队列</li></ul>
              </section>
              <div className="membership-plan-grid">
                {MEMBERSHIP_PLANS.map((plan) => (
                  <button key={plan.id} className={membershipId === plan.id ? "membership-plan active" : "membership-plan"} type="button" onClick={() => setMembershipId(plan.id)}>
                    {"recommended" in plan && plan.recommended && <span className="membership-recommend">推荐</span>}
                    <small>{plan.tag}</small><b>{plan.name}</b><div><strong>{plan.price}</strong><em>{plan.unit}</em></div><p>{plan.credits}</p>
                  </button>
                ))}
              </div>
            </>
          ) : (
            <>
              <section className="credits-summary">
                <span><Zap size={20} fill="currentColor" /></span>
                <div><small>当前可用积分</small><strong>20</strong><p>积分长期有效，可用于所有标有 VIP 的生成模型。</p></div>
              </section>
              <div className="credit-package-grid">
                {CREDIT_PACKAGES.map((item) => (
                  <button key={item.id} className={creditsId === item.id ? "credit-package active" : "credit-package"} type="button" onClick={() => setCreditsId(item.id)}>
                    {"recommended" in item && item.recommended && <span className="membership-recommend">最划算</span>}
                    <span><Zap size={14} fill="currentColor" /></span><strong>{item.amount}</strong><small>积分</small><b>{item.price}</b>{item.gift && <em>{item.gift}</em>}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <footer className="membership-footer">
          <span><ShieldCheck size={13} />支付服务尚未接入，当前仅展示购买流程</span>
          <button type="button" onClick={() => onPurchase(purchaseLabel)}><Sparkles size={15} />确认购买 {purchaseLabel}</button>
        </footer>
      </section>
    </div>
  );
}
