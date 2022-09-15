<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Results</title>
</head>
<body>
   <h1> Results </h1>
   <h2> Unique Posts of {{response['username']}}:</h2>
   <h2>{{response['num_posts']}} Posts:</h2>

    <form method="get" action="/">
       <button type="submit">Return</button>
    </form>
    <ul>
        Subs:
        % for sub in response['subs']:
        <li>{{sub['name']}}:{{sub['size']}} Posts</li>
        % end
    </ul>
   <table>
       <tr>
           <th>Post</th>
           <th>Thumbnail</th>
           <th>Sub</th>
           <th>Upvotes</th>
       </tr>
        % for post in response['posts']:
       <tr>
           <td><a href={{post['post_url']}}> {{post['title']}} </a></td>
           <td>
               <a href={{post['out_url']}}>
                   <img src={{post['thumbnail']}} alt="Thumbnail">
               </a>
           </td>
           <td>{{post['sub']}}</td>
           <td>{{post['upvotes']}}</td>
       </tr>
        % end
   </table>

</body>
</html>