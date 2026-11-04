{{ config(severity = 'warn') }}

-- Avertissement : prix à plus de 40 % de la médiane nationale
-- du même carburant le même jour (saisie douteuse ou prix périmé).
with medianes as (
    select
        jour,
        carburant,
        approx_quantiles(prix, 100)[offset(50)] as prix_median
    from {{ ref('stg_prix_carburants') }}
    group by jour, carburant
)

select
    s.id_station,
    s.ville,
    s.carburant,
    s.jour,
    s.prix,
    m.prix_median,
    round(safe_divide(s.prix - m.prix_median, m.prix_median) * 100, 1) as ecart_pct
from {{ ref('stg_prix_carburants') }} as s
inner join medianes as m
    on s.jour = m.jour
    and s.carburant = m.carburant
where abs(safe_divide(s.prix - m.prix_median, m.prix_median)) > 0.40