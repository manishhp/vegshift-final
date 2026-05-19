import React, { useMemo } from "react";
import type { CoachLanguage } from "../api/types";
import { useLanguage } from "../state/LanguageContext";
import { capitalizeWords } from "../utils/text";

interface ActionStepsProps {
  irrigationMethod: string;
  sowingWindow: string;
  avoidCrops: string[];
  recommendedCrops: string[];
}

const TEXT = {
  en: {
    title: "Action Steps",
    specific: "Specific actions",
    steps: {
      irrigationCheck: "Confirm water source and set up {method} for this season.",
      irrigationDrip: "For drip: install filters, add a pressure regulator, and check emitters.",
      irrigationSprinkler: "For sprinkler: verify nozzle spacing and account for wind direction.",
      rainwater: "Add rainwater harvesting: rooftop collection plus contour trenches.",
      sowingPlan: "Prepare land and seeds so sowing starts {window}.",
      avoidCrops: "Avoid high-water crops now: {crops}.",
      recommendCrops: "Prioritize these crops: {crops}.",
    },
    method: {
      drip: "drip",
      sprinkler: "sprinkler",
      rwh: "rainwater harvesting",
      or: "or",
      with: "with",
      fallback: "recommended irrigation",
    },
  },
  hi: {
    title: "कार्य योजना",
    specific: "ठोस कदम",
    steps: {
      irrigationCheck: "अपने जल स्रोत की जांच करें और इस मौसम के लिए {method} व्यवस्था पक्की करें।",
      irrigationDrip: "ड्रिप के लिए: फ़िल्टर, प्रेशर रेगुलेटर लगाएं और एमिटर जांचें।",
      irrigationSprinkler: "स्प्रिंकलर के लिए: नोज़ल दूरी और हवा की दिशा जांचें।",
      rainwater: "बारिश का पानी संग्रह करें: छत से संग्रह + कंटूर ट्रेंच।",
      sowingPlan: "भूमि और बीज की तैयारी करें ताकि बुआई {window} से पहले हो।",
      avoidCrops: "अभी ये फसलें न लगाएं: {crops}.",
      recommendCrops: "इन फसलों को प्राथमिकता दें: {crops}.",
    },
    method: {
      drip: "ड्रिप",
      sprinkler: "स्प्रिंकलर",
      rwh: "वर्षा जल संचयन",
      or: "या",
      with: "के साथ",
      fallback: "अनुशंसित सिंचाई",
    },
  },
  kn: {
    title: "ಕಾರ್ಯ ಕ್ರಮ",
    specific: "ಸ್ಪಷ್ಟ ಕ್ರಮಗಳು",
    steps: {
      irrigationCheck: "ನಿಮ್ಮ ನೀರಿನ ಮೂಲವನ್ನು ಪರಿಶೀಲಿಸಿ ಮತ್ತು ಈ ಋತುವಿಗೆ {method} ವ್ಯವಸ್ಥೆ ಖಚಿತಪಡಿಸಿ.",
      irrigationDrip: "ಡ್ರಿಪ್‌ಗೆ: ಫಿಲ್ಟರ್, ಒತ್ತಡ ನಿಯಂತ್ರಕ ಹಾಕಿ ಮತ್ತು ಎಮಿಟರ್‌ಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
      irrigationSprinkler: "ಸ್ಪ್ರಿಂಕ್ಲರ್‌ಗೆ: ನೋಜಲ್ ಅಂತರ ಮತ್ತು ಗಾಳಿ ದಿಕ್ಕನ್ನು ಪರಿಶೀಲಿಸಿ.",
      rainwater: "ಮಳೆ ನೀರು ಸಂಗ್ರಹಣೆ ಮಾಡಿ: ಛಾವಣಿ ಸಂಗ್ರಹ + ಕಂಟೂರು ಟ್ರೆಂಚ್.",
      sowingPlan: "ಭೂಮಿ ಮತ್ತು ಬೀಜ ತಯಾರಿಸಿ; ಬಿತ್ತನೆ {window} ಮುನ್ನ ಮಾಡಿರಿ.",
      avoidCrops: "ಈ ಸಮಯದಲ್ಲಿ ಈ ಬೆಳೆಗಳನ್ನು ತಪ್ಪಿಸಿ: {crops}.",
      recommendCrops: "ಈ ಬೆಳೆಗಳಿಗೆ ಆದ್ಯತೆ ಕೊಡಿ: {crops}.",
    },
    method: {
      drip: "ಡ್ರಿಪ್",
      sprinkler: "ಸ್ಪ್ರಿಂಕ್ಲರ್",
      rwh: "ಮಳೆ ನೀರು ಸಂಗ್ರಹಣೆ",
      or: "ಅಥವಾ",
      with: "ಜೊತೆ",
      fallback: "ಶಿಫಾರಸು ಮಾಡಿದ ನೀರಾವರಿ",
    },
  },
} as const;

function formatList(items: string[]): string {
  return items.length ? items.map(capitalizeWords).join(", ") : "None";
}

function methodLabel(method: string, lang: CoachLanguage): string {
  const t = TEXT[lang].method;
  const hasDrip = method.includes("drip");
  const hasSprinkler = method.includes("sprinkler");
  const hasRwh = method.includes("rwh") || method.includes("rain");

  let base: string = t.fallback;
  if (hasDrip && hasSprinkler) {
    base = `${t.drip} ${t.or} ${t.sprinkler}`;
  } else if (hasDrip) {
    base = t.drip;
  } else if (hasSprinkler) {
    base = t.sprinkler;
  }

  return hasRwh ? `${base} ${t.with} ${t.rwh}` : base;
}

function buildRuleSteps(
  irrigationMethod: string,
  sowingWindow: string,
  avoidCrops: string[],
  recommendedCrops: string[],
  lang: CoachLanguage,
): string[] {
  const t = TEXT[lang].steps;
  const steps: string[] = [];
  const method = methodLabel(irrigationMethod, lang);
  steps.push(t.irrigationCheck.replace("{method}", method));

  if (irrigationMethod.includes("drip")) {
    steps.push(t.irrigationDrip);
  }
  if (irrigationMethod.includes("sprinkler")) {
    steps.push(t.irrigationSprinkler);
  }
  if (irrigationMethod.includes("rwh") || irrigationMethod.includes("rain")) {
    steps.push(t.rainwater);
  }
  if (sowingWindow) {
    steps.push(t.sowingPlan.replace("{window}", sowingWindow));
  }
  if (avoidCrops.length) {
    steps.push(t.avoidCrops.replace("{crops}", formatList(avoidCrops)));
  }
  if (recommendedCrops.length) {
    steps.push(t.recommendCrops.replace("{crops}", formatList(recommendedCrops.slice(0, 5))));
  }
  return steps;
}

const ActionSteps: React.FC<ActionStepsProps> = ({
  irrigationMethod,
  sowingWindow,
  avoidCrops,
  recommendedCrops,
}) => {
  const { lang: globalLang } = useLanguage();
  const language = globalLang as CoachLanguage;

  const t = TEXT[language];
  const ruleSteps = useMemo(
    () => buildRuleSteps(irrigationMethod, sowingWindow, avoidCrops, recommendedCrops, language),
    [irrigationMethod, sowingWindow, avoidCrops, recommendedCrops, language]
  );

  return (
    <div className="card action-steps">
      <h4 style={{ margin: 0 }}>{t.title}</h4>
      <div style={{ marginTop: 14 }}>
        <div style={{ fontWeight: 700, marginBottom: 6 }}>{t.specific}</div>
        <ul>
          {ruleSteps.map((step, idx) => (
            <li key={`${idx}-${step.slice(0, 12)}`}>{step}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default ActionSteps;
