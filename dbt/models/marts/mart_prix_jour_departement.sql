-- Prix par jour, département et carburant, calculés uniquement
-- sur les prix récents et non suspects
select
    jour,
    code_region,
    region,
    code_departement,
    departement,
    carburant,
    count(*) as nb_stations,
    round(avg(prix), 3) as prix_moyen,
    approx_quantiles(prix, 100)[offset(50)] as prix_median,
    min(prix) as prix_min,
    max(prix) as prix_max
from {{ ref('int_prix_qualifies') }}
where est_recent and not est_suspect
group by jour, code_region, region, code_departement, departement, carburant