# User manual explaining setup process: Client, Server, Middleware

The game has only one Python's 3rd party module as its dependency -- `pika` -- which is responsible for the middleware, and which uses RabbitMQ broker behind the scenes. Thus, it's imperative to install RabbitMQ server to your machine as well if you want to run the program on a local machine. But this is not necessary as the RabbitMQ broker must not reside on the local machine; instead, some websites (e.g. https://www.cloudamqp.com/) provides services in which the RabbitMQ broker is available over the Internet, assuming appropriate credentials. Since we do not want to publish our credentials (as these can be abused to overload the RabbitMQ server), we use `localhost` hostname and `guest` username as the default. The game provider/gamer is free to modify these connection parameters in `common.py`.

The game should be run in terminal. Some functions (e.g. getpass) may not work properly when using some IDE.

Server is started by the following command:
```
$ python server.py -s <servername>
```

# User manual explaining the user interface and how to play the game

**1.** The user starts the client program with
```
$ python client.py
Getting list of available servers, please wait...
If no servers are seen after 6 seconds, then no server is available.
```
**2.** The client must now wait until he/she can answer the next question.

```
Available servers and number of clients connected:
Server A: 6 client(s)
Server B: 2 client(s)
Server C: 0 client(s)
Would you like to update the list? [y/N]
```

The interpretation of this output is that there is:

* a server named *Server A* which hosts 6 clients;
* a server named *Server B* which hosts 2 clients;
* a server named *Server C* which hosts 0 clients.

The user can request again the list of available servers by entering `y/Y/yes` into the prompt. If the user just wants to proceed w/ the game, an ENTER suffices.

If there are no servers available at all, the screen output won't get past the very initial greeting.

**3.** The client must give the server name in which he/she wants to play.
```
Enter the name of the server you want to connect to: 
```
Entering e.g. `Server B` means that the user now plays on the server named `Server B`.

**4.** The client must authenticate him/herself.
```
Connected to Server B
Enter your username: <username>
Enter your password: <password>
```
where `<username>` and `<password>` are specified by the user.

There are three outcomes to this:

* `This username is taken or you entered a wrong password, please try again.`
* `Sorry, maximum number of players has been exceeded.`
* `Sorry but this user is already logged in.`

Just to clarify the second point, the maximum number of players the server can support is 10 (see point 7 for an argument justifying this limit).

However, if the user has never logged in to the server before, the entered password will be associated to the username from here on out, provided that there were no other authentication errors listed above. In other words, if the user wants to again log in to the server he/she must use the same password as it was created with.

**5.** User waits for other players to join the game server. Analogous text will be printed on the screen periodically:
```
Game not started yet, 7 client(s) connected, <adminusername> has rights to start the game.
```
where `<adminusername>` corresponds to the user who first joined the game server.

**6.** User either starts the game or awaits for the admin to start the game. Non-admin users cannot start the game, though. Admins are greeted w/ the following message just before previous point:
```
Do you want to start the game? [Y/n]
```
Non-admins cannot see this message and can only wait for the admin to start the game. There is only one admin per game session.

**7.** Users play. The ships are placed automatically (yet randomly) by the game server so that none of the ships cross each other between any two users. This, however, means that the game board scale w.r.t the number of gamers. The upside to this solution is that the each user can bomb the field once, not each field individually.

Therefore, each user sees two game boards: his/her own ships and other players' fields merged together (so that there are two fields displayed in total). For example, the admin sees:
```
Hello, <adminusername>! You have connected succesfully!
      1   2   3   4   5   6   7   8   9             1   2   3   4   5   6   7   8   9  
   ------------------------------------          ------------------------------------
A  |  .   5   5   5   5   5   3   3   3       A  |  -   -   -   -   -   -   -   -   -  
B  |  .   .   .   .   .   .   .   .   2       B  |  -   -   -   -   -   -   -   -   -  
C  |  .   .   .   .   .   .   .   .   2       C  |  -   -   -   -   -   -   -   -   -  
D  |  .   .   .   6   .   .   .   .   .       D  |  -   -   -   -   -   -   -   -   -  
E  |  .   .   .   6   .   4   .   .   .       E  |  -   -   -   -   -   -   -   -   -  
F  |  .   .   .   6   .   4   .   .   .       F  |  -   -   -   -   -   -   -   -   -  
G  |  .   .   .   .   .   4   .   .   .       G  |  -   -   -   -   -   -   -   -   -  
H  |  .   .   .   .   .   4   .   .   .       H  |  -   -   -   -   -   -   -   -   -  
Game not started yet, 2 client(s) connected, <adminusername> has rights to start the game.
Enter the coords you want to hit! (ex a2) You have 25 seconds!:
```
Here the left-side field is user's own field, whereas the filed on the right is opponents' fields merged together.
And the other player sees:
```
Hello, <otherusername>! You have connected succesfully!
      1   2   3   4   5   6   7   8   9             1   2   3   4   5   6   7   8   9  
   ------------------------------------          ------------------------------------
A  |  .   .   .   .   .   .   .   .   .       A  |  -   -   -   -   -   -   -   -   -  
B  |  .   .   .   .   5   .   .   .   .       B  |  -   -   -   -   -   -   -   -   -  
C  |  4   4   4   4   5   .   .   .   .       C  |  -   -   -   -   -   -   -   -   -  
D  |  .   2   .   .   5   6   6   6   .       D  |  -   -   -   -   -   -   -   -   -  
E  |  .   2   .   .   5   .   .   .   .       E  |  -   -   -   -   -   -   -   -   -  
F  |  .   .   .   .   5   .   .   .   .       F  |  -   -   -   -   -   -   -   -   -  
G  |  .   .   .   .   .   .   .   .   .       G  |  -   -   -   -   -   -   -   -   -  
H  |  .   .   .   .   .   .   3   3   3       H  |  -   -   -   -   -   -   -   -   -
```
Each player has been given 25 seconds to enter the coordinates. If the entered coordinates are wrong, the user is given another 25 seconds to enter the coordinates until the coordinate pair is valid (even if the coordinate was already bombed -- it's users fault if he/she thinks that bombing the same coordinate would have any effect). However, if the 25 second limit has been reached and the user hasn't entered any coordinates whatsoever, the turn goes to the next player.

There are six types of marks on the fields:

| Symbol    |               Meaning                 |
|:----------|:-------------------------------------:|
| .         |           own water                   |
| \-        |      opponents' unbombed fields       |
| 0         |     no hit on opponents' fields       |
| X         |       a hit on opponents' fields      |
| S         |   sinked ship on opponents' fields    |
| \*        |          bombed own ship              |
| number    | own ship (number tells the ship type) |

One possible state for a user might be:
```
      1   2   3   4   5   6   7   8   9             1   2   3   4   5   6   7   8   9  
   ------------------------------------          ------------------------------------
A  |  .   .   .   .   .   .   .   .   .       A  |  -   -   -   -   -   -   -   -   -  
B  |  .   .   .   .   5   .   .   .   .       B  |  -   -   -   -   -   -   -   -   S  
C  |  *   4   4   4   5   .   .   .   .       C  |  -   -   -   -   -   -   -   -   S  
D  |  .   *   .   .   5   6   6   6   .       D  |  -   -   -   -   -   0   -   -   -  
E  |  .   2   .   .   5   .   .   .   .       E  |  -   -   -   -   -   X   -   -   -  
F  |  .   .   .   .   5   .   .   .   .       F  |  -   -   -   -   -   -   -   -   -  
G  |  .   .   .   .   .   .   .   .   .       G  |  -   -   -   -   -   -   -   -   -  
H  |  .   .   .   .   .   .   3   3   3       H  |  -   -   -   -   -   -   -   -   -
```
Note that the only ambiguity here is that the user doesn't know whose ship has he/she bombed or sinked; the user whose ship has been bombed or sinked does know, who did it.

**8.** Playing 'til there's a winner.

Example output of the player who lost.
```
      1   2   3   4   5   6   7   8   9             1   2   3   4   5   6   7   8   9  
   ------------------------------------          ------------------------------------
A  |  .   .   *   *   .   *   *   *   .       A  |  -   O   -   -  O   O   O   O   -  
B  |  .   .   *   *   .   .   .   .   .       B  |  -   -   O   O   -   -   -   -   -  
C  |  .   .   *   .   .   .   .   .   .       C  |  -   -   O   -   -   -   -   -   O  
D  |  .   .   *   .   .   .   .   .   *       D  |  -   -   -   O   -   -   -   -   O  
E  |  .   .   .   .   .   .   .   .   *       E  |  X   O   -   X   -   -   X   -   -  
F  |  .   .   .   .   .   .   .   .   *       F  |  X   -   -   -   -   -   X   -   -  
G  |  .   *   *   *   .   .   .   .   *       G  |  -   O   O   O   -   -   -   -   -  
H  |  .   .   .   .   .   .   .   .   *       H  |  -   -   -   -   -   -   -   -   O  

You have lost, sorry. <winnerusername> is user!
```

Example output on the winners screen. On the right, all of the ships have been sinked.
```
      1   2   3   4   5   6   7   8   9             1   2   3   4   5   6   7   8   9  
   ------------------------------------          ------------------------------------
A  |  .   .   .   .   .   .   .   .   .       A  |  O   -   S   S   O   S   S   S   -  
B  |  .   .   .   .   .   6   .   .   .       B  |  -   -   S   S   -   -   -   -   -  
C  |  .   .   .   .   .   6   .   .   .       C  |  -   -   S   -   -   -   -   -   O  
D  |  5   .   .   .   .   6   .   .   .       D  |  -   -   S   O   -   -   -   -   S  
E  |  *   .   .   *   4   4   *   .   .       E  |  -   -   -   -   -   -   -   -   S  
F  |  *   .   .   .   3   3   *   .   .       F  |  -   -   -   -   -   -   -   -   S  
G  |  5   .   .   .   .   .   .   .   .       G  |  -   S   S   S   -   -   -   -   S  
H  |  5   .   .   .   2   2   .   .   .       H  |  -   -   -   -   -   -   -   -   S  
Good job, you have won!
```
