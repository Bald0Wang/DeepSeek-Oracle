import { useEffect, useRef } from "react";


interface Point {
  x: number;
  y: number;
}

interface BackgroundStar {
  x: number;
  y: number;
  radius: number;
  alpha: number;
  drift: number;
  phase: number;
}

interface DustParticle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  phase: number;
}


const TAU = Math.PI * 2;
const TRANSITION_DURATION = 1800;

const CONSTELLATION_LINKS: Array<[number, number]> = [
  [0, 1],
  [1, 2],
  [2, 3],
  [3, 4],
  [4, 5],
  [5, 6],
  [6, 7],
  [7, 8],
  [8, 9],
  [9, 2],
  [2, 4],
  [4, 8],
];

const CONSTELLATIONS: Point[][] = [
  [
    { x: 0.14, y: 0.18 },
    { x: 0.22, y: 0.12 },
    { x: 0.35, y: 0.22 },
    { x: 0.46, y: 0.17 },
    { x: 0.58, y: 0.27 },
    { x: 0.72, y: 0.2 },
    { x: 0.84, y: 0.3 },
    { x: 0.66, y: 0.41 },
    { x: 0.5, y: 0.45 },
    { x: 0.3, y: 0.37 },
  ],
  [
    { x: 0.2, y: 0.14 },
    { x: 0.32, y: 0.1 },
    { x: 0.46, y: 0.16 },
    { x: 0.62, y: 0.13 },
    { x: 0.76, y: 0.22 },
    { x: 0.72, y: 0.36 },
    { x: 0.6, y: 0.44 },
    { x: 0.46, y: 0.46 },
    { x: 0.34, y: 0.4 },
    { x: 0.22, y: 0.3 },
  ],
  [
    { x: 0.16, y: 0.22 },
    { x: 0.25, y: 0.11 },
    { x: 0.4, y: 0.14 },
    { x: 0.54, y: 0.1 },
    { x: 0.7, y: 0.18 },
    { x: 0.82, y: 0.3 },
    { x: 0.74, y: 0.42 },
    { x: 0.58, y: 0.48 },
    { x: 0.43, y: 0.42 },
    { x: 0.26, y: 0.35 },
  ],
];


const randomBetween = (min: number, max: number) => min + Math.random() * (max - min);

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const lerp = (from: number, to: number, progress: number) => from + (to - from) * progress;

const easeInOutCubic = (value: number) =>
  value < 0.5 ? 4 * value * value * value : 1 - Math.pow(-2 * value + 2, 3) / 2;

const createBackgroundStars = (width: number, height: number): BackgroundStar[] => {
  const count = Math.max(180, Math.floor((width * height) / 5600));
  return Array.from({ length: count }, () => ({
    x: randomBetween(0, width),
    y: randomBetween(0, height),
    radius: randomBetween(0.6, 2.3),
    alpha: randomBetween(0.24, 0.95),
    drift: randomBetween(0.2, 2.2),
    phase: randomBetween(0, TAU),
  }));
};

const createDustParticles = (width: number, height: number): DustParticle[] => {
  const count = Math.max(58, Math.floor((width * height) / 17500));
  return Array.from({ length: count }, () => ({
    x: randomBetween(0, width),
    y: randomBetween(0, height),
    vx: randomBetween(-4.5, 4.5),
    vy: randomBetween(-10, -2.5),
    size: randomBetween(0.8, 2.1),
    phase: randomBetween(0, TAU),
  }));
};

const blendConstellation = (from: Point[], to: Point[], progress: number) =>
  from.map((point, index) => {
    const target = to[index] ?? point;
    return {
      x: lerp(point.x, target.x, progress),
      y: lerp(point.y, target.y, progress),
    };
  });


interface ZiweiBackgroundProps {
  activeIndex: number;
}


export function ZiweiBackground({ activeIndex }: ZiweiBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const activeIndexRef = useRef(((activeIndex % CONSTELLATIONS.length) + CONSTELLATIONS.length) % CONSTELLATIONS.length);
  const renderStaticRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    activeIndexRef.current = ((activeIndex % CONSTELLATIONS.length) + CONSTELLATIONS.length) % CONSTELLATIONS.length;
    if (renderStaticRef.current) {
      renderStaticRef.current();
    }
  }, [activeIndex]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

    let width = 0;
    let height = 0;
    let dpr = 1;

    let backgroundStars: BackgroundStar[] = [];
    let dustParticles: DustParticle[] = [];

    let reduceMotion = motionQuery.matches;
    let rafId = 0;
    let elapsed = 0;
    let previousTime = performance.now();

    let activeConstellation = activeIndexRef.current;
    let nextConstellation = activeIndexRef.current;
    let transitionStartAt = -1;

    const mapToScreen = (shape: Point[]) => {
      const scale = Math.min(width, height) * 0.62;
      const centerX = width * 0.5;
      const centerY = height * 0.38;

      return shape.map((point, index) => ({
        x: centerX + (point.x - 0.5) * scale,
        y: centerY + (point.y - 0.5) * scale,
        radius: clamp(scale * 0.005 + (index % 3) * 0.24, 1.2, 3.4),
      }));
    };

    const drawGalaxy = (time: number) => {
      const driftX = Math.sin(time * 0.00012) * width * 0.04;
      const driftY = Math.cos(time * 0.00009) * height * 0.03;

      const coreX = width * 0.52 + driftX;
      const coreY = height * 0.34 + driftY;

      const coreGradient = context.createRadialGradient(
        coreX,
        coreY,
        0,
        coreX,
        coreY,
        Math.max(width, height) * 0.46
      );
      coreGradient.addColorStop(0, "rgba(142, 195, 255, 0.32)");
      coreGradient.addColorStop(0.26, "rgba(247, 178, 235, 0.2)");
      coreGradient.addColorStop(0.6, "rgba(119, 141, 208, 0.12)");
      coreGradient.addColorStop(1, "rgba(20, 30, 60, 0)");

      context.fillStyle = coreGradient;
      context.fillRect(0, 0, width, height);

      context.save();
      context.translate(coreX, coreY);
      context.rotate(time * 0.00006);
      context.lineWidth = clamp(Math.min(width, height) * 0.0014, 0.8, 2.2);

      for (let index = 0; index < 3; index += 1) {
        context.beginPath();
        context.strokeStyle = `rgba(217, 190, 255, ${0.18 - index * 0.04})`;
        context.ellipse(
          0,
          0,
          Math.min(width, height) * (0.28 + index * 0.06),
          Math.min(width, height) * (0.11 + index * 0.03),
          (Math.PI / 3) * index,
          0.15 * Math.PI,
          1.42 * Math.PI
        );
        context.stroke();
      }

      context.restore();
    };

    const drawBackgroundStars = () => {
      backgroundStars.forEach((star, index) => {
        const twinkle = 0.4 + (Math.sin(elapsed * 1.1 + star.phase + index * 0.13) + 1) * 0.32;
        const alpha = clamp(star.alpha * twinkle, 0.14, 1);
        const y = (star.y + Math.sin(elapsed * 0.18 + star.phase) * star.drift + height) % height;

        context.globalAlpha = alpha;
        context.fillStyle = "#ffffff";
        context.beginPath();
        context.arc(star.x, y, star.radius, 0, TAU);
        context.fill();
      });

      context.globalAlpha = 1;
    };

    const drawDustParticles = (deltaSeconds: number, staticFrame: boolean) => {
      dustParticles.forEach((particle, index) => {
        if (!staticFrame) {
          particle.x += particle.vx * deltaSeconds;
          particle.y += particle.vy * deltaSeconds;

          if (particle.x < -18) {
            particle.x = width + 18;
          } else if (particle.x > width + 18) {
            particle.x = -18;
          }

          if (particle.y < -18) {
            particle.y = height + 18;
            particle.x = randomBetween(0, width);
          }
        }

        const pulse = 0.15 + (Math.sin(elapsed * 1.4 + particle.phase + index * 0.2) + 1) * 0.13;
        context.fillStyle = `rgba(235, 239, 255, ${pulse.toFixed(3)})`;
        context.beginPath();
        context.arc(particle.x, particle.y, particle.size, 0, TAU);
        context.fill();
      });
    };

    const drawConstellation = (time: number, staticFrame: boolean) => {
      const desiredIndex = activeIndexRef.current;

      if (staticFrame) {
        activeConstellation = desiredIndex;
        nextConstellation = desiredIndex;
        transitionStartAt = -1;
      } else if (transitionStartAt < 0 && desiredIndex !== activeConstellation) {
        nextConstellation = desiredIndex;
        transitionStartAt = time;
      } else if (transitionStartAt >= 0) {
        nextConstellation = desiredIndex;
      }

      let blend = 0;
      if (transitionStartAt > 0) {
        const transitionProgress = clamp((time - transitionStartAt) / TRANSITION_DURATION, 0, 1);
        blend = easeInOutCubic(transitionProgress);

        if (transitionProgress >= 1) {
          activeConstellation = nextConstellation;
          nextConstellation = (nextConstellation + 1) % CONSTELLATIONS.length;
          transitionStartAt = -1;
          blend = 0;
        }
      }

      const from = CONSTELLATIONS[activeConstellation];
      const to = CONSTELLATIONS[nextConstellation];
      const points = mapToScreen(blendConstellation(from, to, blend));

      const centerX = width * 0.5;
      const centerY = height * 0.38;
      const scale = Math.min(width, height) * 0.62;

      context.save();
      context.translate(centerX, centerY);
      context.rotate(elapsed * 0.09);
      context.strokeStyle = "rgba(248, 205, 255, 0.24)";
      context.lineWidth = clamp(scale * 0.0022, 0.8, 1.8);
      context.beginPath();
      context.ellipse(0, 0, scale * 0.34, scale * 0.17, 0, 0, TAU);
      context.stroke();
      context.restore();

      context.lineWidth = clamp(scale * 0.0022, 0.9, 2.1);
      context.strokeStyle = "rgba(166, 202, 255, 0.42)";
      context.beginPath();
      CONSTELLATION_LINKS.forEach(([fromIndex, toIndex]) => {
        const start = points[fromIndex];
        const end = points[toIndex];
        context.moveTo(start.x, start.y);
        context.lineTo(end.x, end.y);
      });
      context.stroke();

      context.lineWidth = clamp(scale * 0.0012, 0.6, 1.3);
      context.strokeStyle = "rgba(250, 171, 230, 0.26)";
      context.beginPath();
      CONSTELLATION_LINKS.forEach(([fromIndex, toIndex]) => {
        const start = points[fromIndex];
        const end = points[toIndex];
        context.moveTo(start.x, start.y);
        context.lineTo(end.x, end.y);
      });
      context.stroke();

      points.forEach((point, index) => {
        const pulse = 0.76 + Math.sin(elapsed * 1.5 + index * 0.7) * 0.2;
        const glowRadius = Math.max(14, scale * 0.032) * pulse;

        const glow = context.createRadialGradient(
          point.x,
          point.y,
          0,
          point.x,
          point.y,
          glowRadius
        );
        glow.addColorStop(0, "rgba(255, 255, 255, 1)");
        glow.addColorStop(0.14, "rgba(194, 228, 255, 0.85)");
        glow.addColorStop(0.44, "rgba(246, 182, 238, 0.34)");
        glow.addColorStop(1, "rgba(144, 167, 255, 0)");

        context.fillStyle = glow;
        context.beginPath();
        context.arc(point.x, point.y, glowRadius, 0, TAU);
        context.fill();

        context.fillStyle = "#ffffff";
        context.beginPath();
        context.arc(point.x, point.y, point.radius * pulse, 0, TAU);
        context.fill();

        context.strokeStyle = `rgba(255, 245, 254, ${(0.26 + pulse * 0.18).toFixed(3)})`;
        context.lineWidth = clamp(scale * 0.0011, 0.4, 1);
        context.beginPath();
        context.moveTo(point.x - glowRadius * 0.38, point.y);
        context.lineTo(point.x + glowRadius * 0.38, point.y);
        context.moveTo(point.x, point.y - glowRadius * 0.38);
        context.lineTo(point.x, point.y + glowRadius * 0.38);
        context.stroke();
      });
    };

    const renderFrame = (time: number, staticFrame = false) => {
      const deltaSeconds = staticFrame ? 0 : Math.min((time - previousTime) / 1000, 0.04);
      previousTime = time;
      if (!staticFrame) {
        elapsed += deltaSeconds;
      }

      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      context.clearRect(0, 0, width, height);
      context.fillStyle = "rgba(255, 244, 252, 0.06)";
      context.fillRect(0, 0, width, height);

      drawGalaxy(time);
      drawBackgroundStars();
      drawDustParticles(deltaSeconds, staticFrame);
      drawConstellation(time, staticFrame);
    };

    renderStaticRef.current = () => {
      renderFrame(performance.now(), true);
    };

    const animate = (time: number) => {
      renderFrame(time);
      rafId = window.requestAnimationFrame(animate);
    };

    const stopAnimation = () => {
      if (!rafId) {
        return;
      }
      window.cancelAnimationFrame(rafId);
      rafId = 0;
    };

    const startAnimation = () => {
      if (reduceMotion || rafId) {
        return;
      }
      previousTime = performance.now();
      rafId = window.requestAnimationFrame(animate);
    };

    const resize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      dpr = Math.min(window.devicePixelRatio || 1, 2);

      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      backgroundStars = createBackgroundStars(width, height);
      dustParticles = createDustParticles(width, height);

      renderFrame(performance.now(), true);
    };

    const onVisibilityChange = () => {
      if (document.hidden) {
        stopAnimation();
        return;
      }
      startAnimation();
    };

    const onMotionPreferenceChange = (event: MediaQueryListEvent) => {
      reduceMotion = event.matches;
      if (reduceMotion) {
        stopAnimation();
        renderFrame(performance.now(), true);
        return;
      }
      startAnimation();
    };

    resize();
    if (reduceMotion) {
      renderFrame(performance.now(), true);
    } else {
      startAnimation();
    }

    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", onVisibilityChange);
    motionQuery.addEventListener("change", onMotionPreferenceChange);

    return () => {
      stopAnimation();
      renderStaticRef.current = null;
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      motionQuery.removeEventListener("change", onMotionPreferenceChange);
    };
  }, []);

  return (
    <div className="ziwei-background" aria-hidden="true">
      <div className="ziwei-background__gradient" />
      <div className="ziwei-background__halo" />
      <canvas className="ziwei-background__pixi" ref={canvasRef} />
    </div>
  );
}
