import { Link } from "react-router-dom";

import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { getAccessToken, getStoredUser } from "../utils/auth";

export default function HomePage() {
  const user = getStoredUser();
  const isLoggedIn = Boolean(getAccessToken()) && Boolean(user);

  return (
    <div className="landing-page fade-in">
      <section className="landing-hero fade-in-up">
        <p className="landing-hero__badge">DeepSeek Oracle</p>
        <h1 className="landing-hero__title">天衍 Oracle</h1>
        <p className="landing-hero__subtitle">
          以紫微斗数、梅花易数与心学辅助为核心，提供可追问、可行动、可复盘的东方咨询体验。
        </p>
        <div className="actions-row landing-hero__actions">
          {isLoggedIn ? (
            <>
              <Link to="/start-analysis">
                <InkButton type="button">开始分析</InkButton>
              </Link>
              <Link to="/oracle">
                <InkButton type="button" kind="ghost">进入咨询对话</InkButton>
              </Link>
            </>
          ) : (
            <>
              <Link to="/login">
                <InkButton type="button">用户登录</InkButton>
              </Link>
              <Link to="/register">
                <InkButton type="button" kind="secondary">邮箱注册</InkButton>
              </Link>
            </>
          )}
        </div>
      </section>

      <section className="landing-grid">
        <InkCard title="紫微斗数长线解读" icon="紫">
          <p>面向人生阶段、关系结构与事业方向，给出长期趋势与关键窗口建议。</p>
        </InkCard>
        <InkCard title="梅花易数短期决策" icon="梅">
          <p>围绕近期事件与时间窗口，输出短期倾向、关键变数与应对策略。</p>
        </InkCard>
        <InkCard title="心学辅助与行动化" icon="心">
          <p>将解读结果转为可执行步骤，减少焦虑感，强调可验证、可复盘。</p>
        </InkCard>
      </section>

      <section className="landing-footnote">
        <p>提示：本系统输出仅作参考，不替代医疗、法律、投资等专业建议。</p>
      </section>
    </div>
  );
}
