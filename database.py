import sqlite3
from game_data import locations

conn = sqlite3.connect('database.db')
cursor = conn.cursor()


def init_db():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   player_id TEXT UNIQUE,
                   current_hp INTEGER,
                   damage INTEGER,
                   max_hp INTEGER,
                   current_location_id INTEGER,
                   passed_locations TEXT,
                   current_boss_hp INTEGER,
                   FOREIGN KEY (current_location_id) REFERENCES locations(location_id)
        );''')



    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            location_id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_name TEXT,
            boss_name TEXT,
            boss_hp INTEGER,
            boss_dmg INTEGER,
            hp_bonus INTEGER,
            dmg_bonus INTEGER
        );''')
    
    cursor.executemany('''INSERT OR IGNORE INTO locations 
                    (location_name, boss_name, boss_hp, boss_dmg, hp_bonus, dmg_bonus) 
                    VALUES (?, ?, ?, ?, ?, ?);''', locations)
    conn.commit()   


def save_player(player_id: str, player_data: list):
    with conn:
        cursor.execute('''
            INSERT OR REPLACE INTO players 
            (player_id, current_hp, max_hp, damage, current_location_id, passed_locations, current_boss_hp) 
            VALUES (?, ?, ?, ?, ?, ?, ?);''', [player_id] + player_data)


def load_player(player_id: str) -> dict | None:
    cursor.execute('''SELECT current_hp, max_hp, damage, current_location_id, passed_locations, current_boss_hp
                    FROM players WHERE player_id = ?;''', (player_id,))
    player_data = cursor.fetchone()
    if player_data:
        return {
            'current_hp': player_data[0],
            'max_hp': player_data[1],
            'damage': player_data[2],
            'current_location_id': player_data[3],
            'passed_locations': player_data[4],
            'current_boss_hp': player_data[5]
        }
    

def delete_player(player_id: str):
    with conn:
        cursor.execute('DELETE FROM players WHERE player_id = ?;', (player_id,))
        conn.commit()


def load_locations(loc_id: int | str = None, loc_name: str = None) -> list:
    sql = 'SELECT * FROM locations'
    params = ()

    if loc_id:
        sql += ' WHERE location_id = ?'
        params = (loc_id,)
    elif loc_name:
        sql += ' WHERE location_name = ?'
        params = (loc_name,)
    with conn:
        cursor.execute(sql, params)
        resault = cursor.fetchall()

    #   resault -> [(1, 'Лес', 'Баба яга' ...),()]
    #   data -> [{'id': 1, 'name': 'Лес', 'boss_name': 'Баба яга' ...}, {}]
    data = []
    keys = ['id', 'name', 'boss_name', 'boss_hp', 'boss_dmg', 'hp_bonus', 'dmg_bonus']
    for loc in resault:
        data.append(dict(zip(keys, loc)))
    
    return data


def update_location(player_id: str, loc_id: int|str):
    with conn:
        cursor.execute('UPDATE players SET current_location_id = ? WHERE player_id = ?;', (loc_id, player_id))
        conn.commit()


def update_current_boss_hp(player_id: str, hp: int):
    with conn:
        cursor.execute('UPDATE players SET current_boss_hp = ? WHERE player_id = ?;', (hp, player_id))
        conn.commit()


def pass_location(player_id: str, loc_id: int|str):
    with conn:
        cursor.execute('SELECT passed_locations FROM players WHERE player_id = ?;', (player_id,))
        passed = cursor.fetchone()[0]
    
    if not passed:
        passed = str(loc_id)
    else:
        passed += ',' + str(loc_id)

    with conn:
        cursor.execute('UPDATE players SET passed_locations = ? WHERE player_id = ?;', (passed, player_id))
        conn.commit()


def add_bonus(player_id: str, hp_bonus: int, dmg_bonus: int):
    with conn:
        cursor.execute('SELECT current_hp, damage FROM players WHERE player_id = ?;', (player_id,))
        hp, dmg = cursor.fetchone()
        cursor.execute('UPDATE players SET current_hp = ?, damage = ? WHERE player_id = ?;', (hp + hp_bonus, dmg + dmg_bonus, player_id))
        conn.commit()


def restore_hp(player_id: str):
    with conn:
        cursor.execute('UPDATE players SET current_hp = max_hp WHERE player_id = ?;', (player_id,))
        conn.commit()


def update_hp(player_id: str, player_hp: int, boss_hp: int):
    with conn:
        cursor.execute('UPDATE players SET current_hp = ?, current_boss_hp = ? WHERE player_id = ?;', (player_hp, boss_hp, player_id))
        conn.commit()
    

def check_win(pass_locations: str) -> bool:
    return len(pass_locations.split(',')) == len(locations)