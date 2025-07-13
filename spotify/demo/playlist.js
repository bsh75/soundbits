// Authorization token that must have been created previously. See : https://developer.spotify.com/documentation/web-api/concepts/authorization
const token = 'BQDq78Rom92900G4oq4ubh-VdUbcQ7qLsggyT-masEnwbVh-3sVQ-dr0yIiiGF2yA66qKo-owRUhLqAVPofYh2bwwQLwDvEIrq_UvFxqR8uIqjR1OvugAuk2gCZlAniozKuEcmmmP_gKyNYCeKfn4N5Ilem_WuRZQSCRuRFcmDXpj2o129CO4F8EKYG2doKYV0yF4IrqMoTebNXhP4-c1gNkBWAvy_SEbqlUvsGk6vY1lbZ9TNLz7ie3fj9KOSpxhDWi1hAd5nou5Seu6pjOLxQFlNVW2y_hCZnj5gdr0_Zi2M5y';
async function fetchWebApi(endpoint, method, body) {
  const res = await fetch(`https://api.spotify.com/${endpoint}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    method,
    body:JSON.stringify(body)
  });
  return await res.json();
}

const tracksUri = [
  'spotify:track:1JLn8RhQzHz3qDqsChcmBl','spotify:track:4ByEFOBuLXpCqvO1kw8Wdm','spotify:track:0DrhapFEF5d9Yzg4v914dp','spotify:track:56oReVXIfUO9xkX7pHmEU0','spotify:track:7gkkNoM0zgRc4i42w3tnts'
];

async function createPlaylist(tracksUri){
  const { id: user_id } = await fetchWebApi('v1/me', 'GET')

  const playlist = await fetchWebApi(
    `v1/users/${user_id}/playlists`, 'POST', {
      "name": "My top tracks playlist",
      "description": "Playlist created by the tutorial on developer.spotify.com",
      "public": false
  })

  await fetchWebApi(
    `v1/playlists/${playlist.id}/tracks?uris=${tracksUri.join(',')}`,
    'POST'
  );

  return playlist;
}

const createdPlaylist = await createPlaylist(tracksUri);
console.log(createdPlaylist.name, createdPlaylist.id);
