/*
 * CricketHub MockData
 * ---------------------------------------------------------------------------
 * A device-side (browser localStorage) data store used after deployment.
 * Every user who signs in on a device gets their own data automatically
 * saved on THAT device, keyed by their mobile number.
 *
 * Usage (available as window.MockData):
 *   MockData.isLoggedIn()                  -> bool
 *   MockData.signIn(mobile, extra)         -> user object
 *   MockData.signOut()
 *   MockData.getProfile(mobile)            -> object|null
 *   MockData.saveProfile(mobile, data)     -> bool
 *   MockData.getSubscriptions(mobile)      -> array
 *   MockData.addSubscription(mobile, data) -> bool
 *   MockData.addChatMessage(mobile, text, isUser, isChatbox)
 *   MockData.getChatMessages(mobile[, isChatbox])
 *   MockData.recordGamePlayed(mobile, slug)
 *   MockData.getGamesPlayed(mobile)
 *   MockData.reset()                       -> wipe stored data (seed again)
 */
(function (global) {
    'use strict';

    const DB_KEY = 'crickethub_mockdb';
    const SESSION_KEY = 'crickethub_session';

    const SEED = {
        users: [
            {
                id: 1,
                mobile: '9876543210',
                full_name: 'Demo Player',
                email: 'demo@crickethub.com',
                gender: 'Male',
                location: 'India',
                about: 'I love cricket.',
                avatar_data: '',
                created_at: '2026-01-01T00:00:00.000Z',
            },
            {
                id: 2,
                mobile: '9876501234',
                full_name: 'Captain Kohli',
                email: 'kohli@crickethub.com',
                gender: 'Male',
                location: 'Delhi',
                about: 'Batter and leader.',
                avatar_data: '',
                created_at: '2026-01-01T00:00:00.000Z',
            },
        ],
        profiles: {},
        subscriptions: {},
        chat_messages: {},
        games_played: {},
    };

    function readDB() {
        try {
            const raw = localStorage.getItem(DB_KEY);
            if (!raw) return null;
            return JSON.parse(raw);
        } catch (e) {
            return null;
        }
    }

    function writeDB(db) {
        try {
            localStorage.setItem(DB_KEY, JSON.stringify(db));
            return true;
        } catch (e) {
            return false;
        }
    }

    function getDB() {
        let db = readDB();
        if (!db || typeof db !== 'object') {
            db = JSON.parse(JSON.stringify(SEED));
            writeDB(db);
        }
        return db;
    }

    function toKey(value) {
        return String((value === undefined || value === null) ? '' : value).trim();
    }

    const MockData = {
        VERSION: '1.0.0',

        getDB: getDB,
        saveDB: writeDB,

        reset: function () {
            try {
                localStorage.removeItem(DB_KEY);
                localStorage.removeItem(SESSION_KEY);
            } catch (e) { /* ignore */ }
            return getDB();
        },

        /* ------------------------- session on this device ------------------------- */

        getCurrentUser: function () {
            try {
                const s = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null');
                if (!s || !s.mobile) return null;
                const user = this.getUserByMobile(s.mobile);
                return user || { mobile: toKey(s.mobile), id: s.user_id, full_name: 'Guest Player' };
            } catch (e) {
                return null;
            }
        },

        isLoggedIn: function () {
            return !!this.getCurrentUser();
        },

        getUserByMobile: function (mobile) {
            const key = toKey(mobile);
            if (!key) return null;
            const db = getDB();
            return db.users.find(function (u) { return toKey(u.mobile) === key; }) || null;
        },

        signIn: function (mobile, extra) {
            const key = toKey(mobile);
            if (!key) return null;

            const db = getDB();
            let user = db.users.find(function (u) { return toKey(u.mobile) === key; });

            if (!user) {
                user = {
                    id: db.users.length ? Math.max.apply(null, db.users.map(function (u) { return u.id; })) + 1 : 1,
                    mobile: key,
                    full_name: (extra && extra.full_name) || 'Guest Player',
                    email: (extra && extra.email) || '',
                    gender: (extra && extra.gender) || '',
                    location: (extra && extra.location) || '',
                    about: (extra && extra.about) || '',
                    avatar_data: (extra && extra.avatar_data) || '',
                    created_at: new Date().toISOString(),
                };
                db.users.push(user);
            } else if (extra) {
                Object.keys(extra).forEach(function (field) {
                    if (extra[field] !== undefined && extra[field] !== null && extra[field] !== '') {
                        user[field] = extra[field];
                    }
                });
                user.mobile = key;
                db.users = db.users.map(function (u) { return toKey(u.mobile) === key ? user : u; });
            }
            writeDB(db);

            const session = {
                mobile: key,
                user_id: user.id,
                device: 'responsive-device',
                signed_in_at: new Date().toISOString(),
            };
            try {
                localStorage.setItem(SESSION_KEY, JSON.stringify(session));
            } catch (e) { /* ignore */ }

            this.emitSignIn(user);
            return user;
        },

        signOut: function () {
            try {
                localStorage.removeItem(SESSION_KEY);
            } catch (e) { /* ignore */ }
        },

        emitSignIn: function (user) {
            (this._signInListeners || []).forEach(function (fn) {
                try { fn(user); } catch (e) { /* ignore */ }
            });
        },

        onSignIn: function (callback) {
            if (typeof callback === 'function') {
                if (!this._signInListeners) this._signInListeners = [];
                this._signInListeners.push(callback);
            }
            return this;
        },

        /* ------------------------------- profiles ------------------------------- */

        getProfile: function (mobile) {
            const key = toKey(mobile);
            if (!key) return null;
            const db = getDB();
            return (db.profiles && db.profiles[key]) || null;
        },

        saveProfile: function (mobile, data) {
            const key = toKey(mobile);
            if (!key || !data) return false;
            const db = getDB();
            if (!db.profiles) db.profiles = {};
            db.profiles[key] = Object.assign({}, db.profiles[key], data, { updated_at: new Date().toISOString() });
            writeDB(db);

            const user = db.users.find(function (u) { return toKey(u.mobile) === key; });
            if (user) {
                const merged = Object.assign({}, data);
                Object.keys(merged).forEach(function (f) {
                    if (merged[f]) user[f] = merged[f];
                });
                user.mobile = key;
                writeDB({ users: db.users, profiles: db.profiles, subscriptions: db.subscriptions, chat_messages: db.chat_messages, games_played: db.games_played });
            }
            return true;
        },

        /* ---------------------------- subscriptions ----------------------------- */

        getSubscriptions: function (mobile) {
            const key = toKey(mobile);
            const db = getDB();
            return (db.subscriptions && db.subscriptions[key]) || [];
        },

        addSubscription: function (mobile, sub) {
            const key = toKey(mobile);
            if (!key || !sub) return false;
            const db = getDB();
            if (!db.subscriptions) db.subscriptions = {};
            if (!db.subscriptions[key]) db.subscriptions[key] = [];
            db.subscriptions[key].push(Object.assign({}, sub, { created_at: new Date().toISOString() }));
            return writeDB(db);
        },

        /* ---------------------------- chat messages ----------------------------- */

        getChatMessages: function (mobile, isChatbox) {
            const key = toKey(mobile);
            const db = getDB();
            let list = (db.chat_messages && db.chat_messages[key]) || [];
            if (isChatbox !== undefined) {
                list = list.filter(function (m) { return !!m.is_chatbox === !!isChatbox; });
            }
            return list;
        },

        addChatMessage: function (mobile, text, isUser, isChatbox) {
            const key = toKey(mobile);
            if (!key || !text) return false;
            const db = getDB();
            if (!db.chat_messages) db.chat_messages = {};
            if (!db.chat_messages[key]) db.chat_messages[key] = [];
            db.chat_messages[key].push({
                message: String(text),
                is_user: !!isUser,
                is_chatbox: !!isChatbox,
                created_at: new Date().toISOString(),
            });
            return writeDB(db);
        },

        /* ---------------------------- games played ------------------------------ */

        getGamesPlayed: function (mobile) {
            const key = toKey(mobile);
            const db = getDB();
            return (db.games_played && db.games_played[key]) || [];
        },

        recordGamePlayed: function (mobile, slug) {
            const key = toKey(mobile);
            if (!key || !slug) return false;
            const db = getDB();
            if (!db.games_played) db.games_played = {};
            if (!db.games_played[key]) db.games_played[key] = [];
            if (db.games_played[key].indexOf(slug) === -1) {
                db.games_played[key].push(slug);
            }
            return writeDB(db);
        },

        /* ------------------------------ bootstrap ------------------------------- */

        autoCapture: function () {
            var current = this.getCurrentUser();
            if (current && current.mobile) {
                document.querySelectorAll('[data-mock-profile]').forEach(function (el) {
                    try {
                        var profile = JSON.parse(el.getAttribute('data-mock-profile'));
                        MockData.saveProfile(current.mobile, profile);
                    } catch (e) { /* ignore */ }
                });
            }
        },
    };

    MockData._signInListeners = [];

    if (typeof global !== 'undefined') {
        global.MockData = MockData;
    }
})(window);