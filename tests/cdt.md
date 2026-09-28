# Contemporary Demographic Transition (CDT) Validation Audit

**Evaluation Dataset**: Project 1509 SVEA / Histmap (Stadestér Demographics, Raw MNL, PAVA/Whittaker smoothing)
**Priors**: Human Mortality Database (HMD), UNWPP, Niva et al. (Kummu)

---

## 1. Age/Sex Validation (MNL vs Clamped to Stadestér)

Evaluates the goodness-of-fit ($R^2$) of the raw Multinomial Logit (MNL) baseline probabilities against the final Stadestér age/sex output (post-PAVA, Whittaker graduation, and clamping) using HMD and UNWPP empirical benchmarks.

### Overall Performance
- **Raw MNL Geomean $R^2$**: $0.4932$
- **Clamped Geomean $R^2$**: $0.6196$
- **Improvement ($\Delta R^2$)**: $+0.1264$

### Table 1: Age/Sex $R^2$ Validation by Epoch
| Year | Empirical Source | Sample ($N$ Countries) | Raw MNL $R^2$ | Clamped $R^2$ (Stadestér) | $\Delta R^2$ (Improvement) |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **1850** | HMD | $7$ | $0.7939$ | **$0.9451$** | **$+0.1512$** |
| **1900** | HMD | $10$ | $0.7584$ | **$0.9646$** | **$+0.2062$** |
| **1920** | HMD | $11$ | $0.8562$ | **$0.9577$** | **$+0.1015$** |
| **1940** | HMD | $16$ | $0.7379$ | **$0.9587$** | **$+0.2208$** |
| **1950** | UNWPP | $188$ | $0.6868$ | **$0.7205$** | **$+0.0337$** |
| **1980** | UNWPP | $188$ | $0.5782$ | **$0.6952$** | **$+0.1171$** |
| **2000** | UNWPP | $188$ | $0.3376$ | **$0.4768$** | **$+0.1391$** |
| **2010** | UNWPP | $188$ | $0.2442$ | **$0.3236$** | **$+0.0794$** |
| **2019** | UNWPP | $188$ | $0.1386$ | **$0.2080$** | **$+0.0694$** |

---

## 2. Births & Deaths Validation (Proxy Residuals vs Empirical)

Evaluates proxy birth and death counts against UNWPP and Niva et al. (Kummu) empirical data. The error percentage reflects the discrepancy between inferred proxy natural events and actual historical statistics.

### Table 2: Global Births and Deaths Accuracy by Epoch
| Year | Source | Sample ($N$) | Proxy Births | Empirical Births | Births Error | Proxy Deaths | Empirical Deaths | Deaths Error |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1950** | UNWPP | $158$ | $70,761,392$ | $90,652,000$ | **$-21.94\%$** | $67,397,437$ | $45,780,000$ | **$+47.22\%$** |
| **1980** | UNWPP | $153$ | $98,436,205$ | $125,518,000$ | **$-21.58\%$** | $72,634,161$ | $44,824,000$ | **$+62.04\%$** |
| **2000** | Kummu + UNWPP | $188$ | $165,919,548$ | $148,120,044$ | **$+12.02\%$** | $22,398,012$ | $62,030,731$ | **$-63.89\%$** |
| **2010** | Kummu + UNWPP | $188$ | $115,164,666$ | $147,031,331$ | **$-21.67\%$** | $80,228,049$ | $62,442,366$ | **$+28.48\%$** |
| **2019** | Kummu + UNWPP | $188$ | $135,131,921$ | $146,561,142$ | **$-7.80\%$** | $59,450,623$ | $66,455,827$ | **$-10.54\%$** |

---

*Generated autonomously by Project 1509 SVEA Contemporary Demographic Transition Validation Engine.*