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

For ready-made data analysis over desktop/mobile clients, you may find it useful to view the NWM over [Confoederatio Dataview](https://dataview.confoederatio.org/), since its raw download size can be very large (80GB+).

<div align = "center">
  <img src = "https://i.postimg.cc/wjLr09mJ/stadester-eoscala.png" width = "100%"><br><br>
  Left: Selected population, urban growth, and sampling data from Stadestér/Velkscala, alongside testing and validation benchmarks.<br>
  Right: Estimated GDP PPP data from Eoscala (3000BC-2020AD).
</div>

#### Histmap:

> **Note.** Stadestér refers to urban data, whereas Velkscala refers to population data generally, including ALCC/LU models.

Methods reports currently lag several versions behind where they should be. For internal methods notes and reports, please contact a CRD member. We also try to keep summary methodologies up-to-date on [Confoederatio Dataview](https://dataview.confoederatio.org/) per indicator.

- Atlas: (Vector) - De facto and de jure polity borders from 3000-2025AD.
  - [[Atlas 0.7] (Datavault)](https://datavault.confoederatio.org/s/rPntqXwCxzXg4Bk) | [Atlas 0.5-0.6 Legacy](https://confoederatio.org/pages/atlas) | [Atlas 0.5 (Sources)](https://confoederatiodocs.info/CRD+(Confoederatio%2C+Research+Division)/Documentation/Notes+%26+Scripts/Atlas+0.5+Sources)
  - **Note.** De facto frontiers are modelled at daily resolution, whilst de jure frontiers are sub-yearly at most, since they conjoin Seshat, Correlates of War, and C-Shapes 2.0.
- Eoscala: (Raster) - Economic estimates from 10000BC-2025AD at 5-arcmin resolution. Tabular national accounts data since 1800AD at yearly resolution.
  - [[Eoscala 1.5] (Datavault)](https://datavault.confoederatio.org/s/2Kytdej7ABpw4rr) | [Eoscala 1.0 (Methodology)](https://confoederatio.org/papers/Eoscala%201.0_Velkscala%200.5%20-%20A%20Gridded%20Reconstruction%20of%20Global%20GDP%20and%20Population%20from%2010000BC%20to%20the%20Present.pdf)
- Stadestér: (Vector) - Discrete urban data for 41k+ cities between 3000BC-2025AD at annual resolution. Yearly urban extents are made available from 1800AD onwards. Historical names and capital city histories included.
  - [[Stadestér 1.1] (Datavault)](https://datavault.confoederatio.org/s/QcXSrmcA7qYSmR6) | [Stadestér 1.0/Velkscala 0.7 (Methodology)](https://doi.org/10.5281/zenodo.17180328)
- Velkscala: (Raster/Vector) - Aggregate population estimates, land use, and ALCC from 10000BC-2025AD. Urban data can be found under <ins>Stadestér</ins>.
  - [[Velkscala 1.0] (Datavault)](https://datavault.confoederatio.org/s/44Pfgt7ya8wE77b) | [Velkscala 1.0 Modelling Report](https://confoederatio.org/papers/Velkscala%20Modelling%20Report%20-%208%20October%202026.pdf) | [Stadestér 1.0/Velkscala 0.7 (Methodology)](https://doi.org/10.5281/zenodo.17180328)
 
<div align = "center">
  <img src = "https://i.postimg.cc/VkhQL7Cp/17-velkscala.png" width = "50%"><br><br>
  Land-use reconstructions for Velkscala vs. LUH2.
</div>

#### Livemap:

- Collation (Vector) - ORBATs, territorial control, and geospatialised news aggregation. Scripts for self-hosting are available [here](https://github.com/Confoederatio/Collation).
- Harbinger - Turns arbitrary, noisy image data and text-scrapes into georeferenced geometries/ontologies using CV/ML techniques. Recommended only for higher-end devices.
  - [[Toolkit (Github)]](https://github.com/ConfoederatioVF/Harbinger) | [[Harbinger.Deprojector]](https://github.com/ConfoederatioVF/Harbinger.Deprojector) | [[Harbinger.Segmentation]](https://github.com/ConfoederatioVF/Harbinger.Segmentation)

</details>
