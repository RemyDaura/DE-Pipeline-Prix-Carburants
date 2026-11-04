with source as (
    select * from {{ source('raw', 'prix_carburants') }}
),

-- Le pipeline peut tourner plusieurs fois par jour :
-- on garde le dernier relevé de chaque station pour chaque jour
dernier_releve_du_jour as (
    select *
    from source
    where true
    qualify row_number() over (
        partition by id, date(extrait_le, 'Europe/Paris')
        order by extrait_le desc
    ) = 1
),

-- Une ligne par station et par carburant.
-- Les carburants sans prix ni date sont écartés automatiquement par UNPIVOT.
par_carburant as (
    select *
    from dernier_releve_du_jour
    unpivot (
        (prix, maj) for carburant in (
            (gazole_prix, gazole_maj) as 'Gazole',
            (sp95_prix, sp95_maj) as 'SP95',
            (sp98_prix, sp98_maj) as 'SP98',
            (e10_prix, e10_maj) as 'E10',
            (e85_prix, e85_maj) as 'E85',
            (gplc_prix, gplc_maj) as 'GPLc'
        )
    )
)

select
    id as id_station,
    date(extrait_le, 'Europe/Paris') as jour,
    carburant,
    prix,
    safe_cast(maj as timestamp) as prix_maj_le,
    adresse,
    cp,
    ville,
    code_departement,
    departement,
    code_region,
    region,
    pop,
    geom_lat,
    geom_lon,
    horaires_automate_24_24,
    extrait_le
from par_carburant