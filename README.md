# Naissance Collation

> [!NOTE]
> For information on the developed product, please view [Naissance HGIS](https://github.com/Confoederatio/Naissance). This repository is mainly intended for programmers and academics.

<img src = "https://i.postimg.cc/Nj195psm/35-collation.png">

<img src = "https://i.postimg.cc/3ND2B1zL/crd-coat-of-arms-logo.png" height = "48"> <img src = "https://i.postimg.cc/76Nn0qx4/collation-logo.png" height = "48">

[![Join our community!](https://img.shields.io/discord/548994743925997570?label=Discord&style=for-the-badge)](https://discord.gg/89kQY2KFQz) ![](https://img.shields.io/github/languages/code-size/Australis-0/Naissance?style=for-the-badge)

- E-mail: [vf@confoederatio.org](mailto:vf@confoederatio.org)
- Documentation (Naissance): [confoederatiodocs.info](https://confoederatiodocs.info/CRD+(Confoederatio%2C+Research+Division)/Documentation/Software/Naissance+HGIS/Naissance+HGIS)
- Documentation (Vercengen): [confoederatio.org/Vercengen](https://confoederatio.org/Vercengen/)

### Abstract.

**Naissance Collation** refers to the software that produces a digital clone of Earth used by [Naissance HGIS](https://github.com/Confoederatio/Naissance/) in both its Histmap/Livemap pre-made datasets. It is made up of many layers, hence <ins>Collation</ins>. **Livemap** refers to real-time mapping, whereas **Histmap** refers to proxy models and datasets relating to past events on Earth. Combined, they form a complete model of the world.

Since the original data sources used in historical modelling as well as Livemap Ontologies are very large, they cannot be stored on GitHub and are available upon request or can be manually populated from references. If you do not have the programming and search engine knowledge necessary to make this happen, turn back now to use Naissance HGIS instead.

### Development.

Prototype features are also added to Collation, and due to the rapid pace of development, it is recommended for any builds to be synced to the dev branch. We will not be issuing releases for Collation - mainstream releases are reserved for the main Naissance repository. In addition, static images of datasets are also posted and made available on their respective repositories when feasible.

### Collation Datasets.

> [!NOTE]
> This section is largely borrowed from Naissance HGIS.

For ready-made data analysis, you may find it useful to use Confoederatio histmaps/livemaps instead. We typically divide such datasets as follows, along with corresponding metadata.

<div align = "center">
  <img src = "https://i.postimg.cc/wjLr09mJ/stadester-eoscala.png" width = "100%"><br><br>
  Left: Selected population, urban growth, and sampling data from Stadestér/Velkscala, alongside testing and validation benchmarks.<br>
  Right: Estimated GDP PPP data from Eoscala (3000BC-2020AD)
</div>

#### Histmap:

> Stadestér refers to urban data, whereas Velkscala refers to population data generally.

- Atlas: (Vector) - Polity data from 3000BC-2023AD, based off [Cliopatria](https://www.nature.com/articles/s41597-025-04516-9), and currently undergoing manual cleaning. Interpreter scripts can be found at Collation in the `livemap` folder, and cleaned polygons at `saves/atlas.naissance`.
- Eoscala: (Raster) - Economic estimates (GDP PPP) from 10000BC-2023AD, (Gini) from 21500BC-1800AD [[point-based]](https://docs.google.com/spreadsheets/d/1WAn29290A2empQgYbvkp-qGcqMCtfyfz5DQ7I5p_rqs/edit?gid=0#gid=0) at 5-arcmin resolution.
  - [[Dataset]](https://github.com/Confoederatio/Eoscala-Velkscala) | [[Methodology]](https://confoederatio.org/papers/Eoscala%201.0_Velkscala%200.5_%20A%20Gridded%20Reconstruction%20of%20Global%20GDP%20and%20Population%20from%2010000BC%20to%20the%20Present-4.pdf)
- Stadestér/Velkscala: (Raster/Vector) - Population estimates (rural, urban, total), land use and ALCC (from HYDE/LUH2KK10) from 10000BC-2025AD. Urban extents and locations are given as GeoJSON datasets, with individual pop. estimates for 41k+ cities between 3000BC-2025AD. Yearly urban extents are made available from 1800AD cities. 5-arcmin resolution.
  - [[Dataset (Github)]](https://github.com/Confoederatio/Stadester) | [[Dataset (Zenodo)]](https://zenodo.org/records/17180328) | [[Methodology]](https://confoederatio.org/papers/Stadest%C3%A9r%201.0%20-%20A%20Global%20Database%20of%2041000%2B%20Cities%20From%203000BC%20to%20the%20Present.pdf)

#### Livemap:

- Collation (Vector) - ORBATs and geospatialised news aggregation. Scripts for self-hosting are available [here](https://github.com/Confoederatio/Collation).
- Deprojector (Beta; Raster) - Arbitrary projection-to-projection georeferencing using ML. These scripts are currently a proof-of-concept and not recommended for production.
  - [[Tool (Github)]](https://github.com/Confoederatio/Deprojector) 
