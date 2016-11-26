#!/usr/bin/env python
import argparse
import logging
from getpass import getpass

from pandas import DataFrame, Series
import numpy as np

import pogo.util as util
from pogo.api import PokeAuthSession
from pogo.pokedex import pokedex

FNAME_PATTERN = 'pokemons_{username}.csv'

IGNORE = {
    pokedex.BULBASAUR,
    pokedex.CHARMANDER,
    pokedex.SQUIRTLE,
    pokedex.NIDORAN_MALE,
    pokedex.ODDISH,
    pokedex.ABRA,
    pokedex.MACHOP,
    pokedex.BELLSPROUT,
    pokedex.DRATINI,
}

# Entry point
# Start off authentication and demo
if __name__ == '__main__':
    util.setupLogger()
    logging.debug('Logger set up')

    # Read in args
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", help="Username", required=True)
    parser.add_argument("-p", "--password", help="Password")
    args = parser.parse_args()

    if args.username:
        username = args.username
    else:
        username = input()
    if args.password:
        password = args.password
    else:
        password = getpass()
    auth = 'google'

    # Create PokoAuthObject
    auth_session = PokeAuthSession(
        username,
        password,
        auth,
        None,
    )

    session = auth_session.authenticate()

    # Time to show off what we can do
    if session:
        # Wait for a second to prevent GeneralPogoException
        # Goodnight moon. Goodnight moon.
        # time.sleep(1)

        # General
        inventory = session.getInventory()

        expanded_candies = {
            pokemon: inventory.candies.get(pokedex.families.get(pokemon, 0), 0)
            for pokemon in pokedex
        }

        expanded_candy_distance = {
            pokemon: pokedex.candy_distance.get(pokedex.families.get(pokemon, 0), 0)
            for pokemon in pokedex
        }

        pokemon_id_list = list(map(lambda p: p.pokemon_id, inventory.party))
        pokemon_counts = {
            pokemon: pokemon_id_list.count(pokemon) for pokemon in pokedex
        }

        pokemon_is_new = {
            pokemon: (pokemon not in inventory.pokedex or
                      inventory.pokedex[pokemon].times_captured == 0)
            for pokemon in pokedex
        }
        evolve_is_new = {
            pokemon: (
                pokedex.families.get(pokemon, 0) == pokedex.families.get(pokemon + 1, 0) and
                pokemon_is_new.get(pokemon + 1, False)
            ) for pokemon in pokedex
        }
        ignore_list = {
            pokemon: (
                pokemon in IGNORE or
                (
                    pokedex.families.get(pokemon, 0) == pokedex.families.get(pokemon + 1, 0) and
                    evolve_is_new[pokemon + 1]
                ) or (
                    pokedex.families.get(pokemon, 0) == pokedex.families.get(pokemon - 1, 0) and
                    not evolve_is_new[pokemon]
                )
            )
            for pokemon in pokedex
        }

        # source columns
        columns = {
            'name': Series(pokedex).apply(lambda x: x.capitalize()),
            'count': Series(pokemon_counts),
            'candies': Series(expanded_candies),
            'evolves': Series(pokedex.evolves),
            'walks': Series(expanded_candy_distance),
            'new': Series(evolve_is_new).apply(int),
            'ign': Series(ignore_list).apply(int)
        }

        # computed columns
        columns['missing'] = columns['evolves'] - columns['candies'] % columns['evolves']
        columns['missing_distance'] = columns['missing'] * columns['walks']
        columns['could_evolve'] = columns['candies'] // columns['evolves']
        columns['can_evolve'] = (
            np.minimum(columns['could_evolve'], columns['count']) * np.logical_not(columns['ign'])
        )
        columns['score'] = 500 * (
            columns['can_evolve'] + np.logical_and(columns['new'], columns['can_evolve'])
        )
        columns['score 2x'] = 2 * columns['score']

        # DataFrame
        data = DataFrame(
            columns,
            columns=[
                'name', 'evolves', 'walks', 'ign', 'new', 'candies', 'count',
                'missing', 'missing_distance', 'can_evolve', 'score', 'score 2x'
            ],
        )
        data = data[data['evolves'] > 0]
        # data = data[data['ign'] == 0]

        stats = DataFrame({
            'new': sum(data[data['can_evolve'] > 0]['new']),
            'can_evolve': sum(data['can_evolve']),
        }, index=['stats'])

        # print(filtered_data.to_csv())
        print(data)
        print(stats)

        with open(FNAME_PATTERN.format(username=username), 'w') as f:
            f.write(data.to_csv())
    else:
        logging.critical('Session not created successfully')
