-- Prix par jour, département et carburant, calculés uniquement
-- sur les prix récents et non suspects
with par_departement as (
    select
        jour,
        code_region,
        region,
        code_departement,
        departement,
        carburant,
        count(*) as nb_stations,
        sum(prix) as somme_prix,
        round(avg(prix), 3) as prix_moyen,
        approx_quantiles(prix, 100)[offset(50)] as prix_median,
        min(prix) as prix_min,
        max(prix) as prix_max
    from {{ ref('int_prix_qualifies') }}
    where est_recent and not est_suspect
    group by jour, code_region, region, code_departement, departement, carburant
)

select
    *,
    -- Moyenne nationale exacte : somme de tous les prix / nombre de stations
    round(
        sum(somme_prix) over (partition by jour, carburant)
        / sum(nb_stations) over (partition by jour, carburant),
        3
    ) as prix_moyen_national,
    round(
        somme_prix / nb_stations
        - sum(somme_prix) over (partition by jour, carburant)
        / sum(nb_stations) over (partition by jour, carburant),
        3
    ) as ecart_au_national
from par_departement