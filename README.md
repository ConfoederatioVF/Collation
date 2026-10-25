# Collation

> [!NOTE]
> For information on the developed product, please view [Naissance HGIS](https://github.com/Confoederatio/Naissance). This repository is mainly intended for programmers and academics.

<img src = "https://i.postimg.cc/Nj195psm/35-collation.png">

<img src = "https://i.postimg.cc/3ND2B1zL/crd-coat-of-arms-logo.png" height = "48"> <img src = "https://i.postimg.cc/76Nn0qx4/collation-logo.png" height = "48">

[![Join our community!](https://img.shields.io/discord/548994743925997570?label=Discord&style=for-the-badge)](https://discord.gg/89kQY2KFQz) ![](https://img.shields.io/github/languages/code-size/ConfoederatioVF/Collation?style=for-the-badge)

- E-mail: [vf@confoederatio.org](mailto:vf@confoederatio.org)
- Documentation (Naissance): [docs.confoederatio.org/Naissance](https://docs.confoederatio.org/en/Naissance)
- Documentation (Vercengen): [confoederatio.org/Vercengen](https://confoederatio.org/Vercengen/)

### Abstract.

**Collation** is a monorepo fork of [Naissance HGIS](https://github.com/Confoederatio/Naissance/) used for producing the <ins>Naissance World Model</ins> (NWM). It is also often used as a testbed for developing new Naissance GIS capabilities. The NWM is split up into **Livemap** and **Histmap** components. Livemap refers to real-time mapping, whereas Histmap refers to proxy models and datasets relating to past events on Earth. Combined, they form a complete model of the world.

Since the original data sources used in historical modelling as well as Livemap Ontologies are very large, they cannot be stored on GitHub and are available upon request or can be manually populated from references. If you do not have the programming and search engine knowledge necessary to make this happen, turn back now to use Naissance HGIS instead.

### Development.

Prototype features are also added to Collation, and due to the rapid pace of development, it is recommended for any builds to be synced to the dev branch. We will not be issuing releases for Collation - mainstream releases are reserved for the main Naissance repository. In addition, static images of datasets are also posted and made available on their respective repositories when feasible.

<details open>
  <summary><h3>Naissance World Model.</h3></summary>

For ready-made data analysis, you may find it useful to use Confoederatio histmaps/livemaps instead. We typically refer to the collection of all our datasets as the **Naissance World Model**, which is divided as follows alongside corresponding metadata.

<div align = "center">
  <img src = "https://i.postimg.cc/wjLr09mJ/stadester-eoscala.png" width = "100%"><br><br>
  Left: Selected population, urban growth, and sampling data from Stadestér/Velkscala, alongside testing and validation benchmarks.<br>
  Right: Estimated GDP PPP data from Eoscala (3000BC-2020AD)
</div>

#### Histmap:

> **Note.** Stadestér refers to urban data, whereas Velkscala refers to population data generally, including ALCC/LU models.

- Atlas: (Vector) - De facto polity extents from 3000BC-2026AD, GeoJSON. Sub-yearly resolution. De jure polity extents from C-Shapes 2.0.
  - [[Dataset (.json)]](https://confoederatio.org/data/atlas_0.5b.json) | [[Dataset (.naissance)]](https://confoederatio.org/data/atlas_0.5b.naissance) | [[Timelapse]](https://www.youtube.com/watch?v=Kc0zNfiAd8c) | [[Webview]](https://confoederatio.org/pages/dataview)
  - **Note.** Daily resolution keyframes, as shown in certain devlogs, are available upon request from [Confoederatio Datavault](https://datavault.confoederatio.org/). Only simplified or compressed versions are uploaded here.
- Eoscala: (Raster) - Economic estimates (GDP PPP, GDP Nominal, GDP PPP pc, GDP Nominal pc) from 10000BC-2025AD, Gini from 10000BC-2025AD at 5-arcmin resolution. Point-based estimates prior to 10000BC.
  - [[Dataset]](https://github.com/Confoederatio/Eoscala-Velkscala) | [[Methodology]](https://confoederatio.org/papers/Eoscala%201.0_Velkscala%200.5%20-%20A%20Gridded%20Reconstruction%20of%20Global%20GDP%20and%20Population%20from%2010000BC%20to%20the%20Present.pdf)
- Stadestér/Velkscala: (Raster/Vector) - Population estimates (rural, urban, total), land use and ALCC (from HYDE/LUH2KK10) from 10000BC-2025AD. Urban extents and locations are given as GeoJSON datasets, with individual pop. estimates for 41k+ cities between 3000BC-2025AD. Yearly urban extents are made available from 1800AD cities. 5-arcmin resolution.
  - [[Dataset (Github)]](https://github.com/Confoederatio/Stadester) | [[Dataset (Zenodo)]](https://zenodo.org/records/17180328) | [[Methodology]](https://confoederatio.org/papers/Stadest%C3%A9r%201.0%20-%20A%20Global%20Database%20of%2041000%2B%20Cities%20From%203000BC%20to%20the%20Present.pdf)
 
<div align = "center">
  <img src = "https://i.postimg.cc/VkhQL7Cp/17-velkscala.png" width = "50%"><br><br>
  Land-use reconstructions for Velkscala vs. LUH2.
</div>

#### Livemap:

- Collation (Vector) - ORBATs, territorial control, and geospatialised news aggregation. Scripts for self-hosting are available [here](https://github.com/Confoederatio/Collation).
- Harbinger - Turns arbitrary, noisy image data and text-scrapes into georeferenced geometries/ontologies using CV/ML techniques. Recommended only for higher-end devices.
  - [[Toolkit (Github)]](https://github.com/ConfoederatioVF/Harbinger) | [[Harbinger.Deprojector]](https://github.com/ConfoederatioVF/Harbinger.Deprojector) | [[Harbinger.Segmentation]](https://github.com/ConfoederatioVF/Harbinger.Segmentation)

</details>
