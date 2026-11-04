with releves as (
    select * from {{ ref('stg_prix_carburants') }}
),

medianes as (
    select
        jour,
        carburant,
        approx_quantiles(prix, 100)[offset(50)] as prix_median_national
    from releves
    group by jour, carburant
)

select
    r.*,
    m.prix_median_national,
    date_diff(r.jour, date(r.prix_maj_le, 'Europe/Paris'), day) as jours_depuis_maj,
    -- Prix mis à jour depuis moins de jours_max_depuis_maj jours (variable dans dbt_project.yml)
    date_diff(r.jour, date(r.prix_maj_le, 'Europe/Paris'), day) <= {{ var('jours_max_depuis_maj') }} as est_recent,
    -- Prix à plus de 40 % de la médiane nationale du carburant ce jour-là
    abs(safe_divide(r.prix - m.prix_median_national, m.prix_median_national)) > 0.40 as est_suspect
from releves as r
inner join medianes as m
    on r.jour = m.jour
    and r.carburant = m.carburant