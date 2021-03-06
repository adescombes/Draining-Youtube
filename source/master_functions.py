from multiprocessing import Manager, Process
from functions import *

MATCH_GEN_FILES = ['geometric_matches',
                   'GeometricAdjacencyMatrix.svg',
                   'matches.f.txt',
                   'matches.putative.bin',
                   'putative_matches',
                   'PutativeAdjacencyMatrix.svg']

####################################### sets functions


def make_sets(v_id, plylst=''):
    """Used after the iter_0 function ran to separate the frames into sets.
    Return the path the to the sets folder"""

    triangles = split_triangles(bin_matches_to_adja_mat(path_mtchs=pth_iter0_mtchs(v_id, plylst),
                                                        path_frames=pth_frms(v_id, plylst)))

    return move_triangles(triangles=triangles,
                          path_vid=pth_vid(v_id, plylst),
                          path_frames=pth_frms(v_id, plylst),
                          path_feats=pth_iter0_feats(v_id, plylst))


def sort_sets(path_vid):
    """Puts sets where the incremental failed in folder Fails"""

    v_id, plylst = get_plylst_id(path_vid)

    sets = pth_sets(v_id, plylst)

    fails_p = os.path.join(sets, 'fails')
    make_dir(fails_p)

    for set in os.listdir(sets):
        set_p = os.path.join(sets, set) # move fails in fail folder
        if os.path.isdir(os.path.join(set_p, 'incremental_fail')):
            os.renames(old=set_p, new=os.path.join(fails_p, set))


#######################################  iter0 and sfm_pipe


def iter0(v_id, plylst='', rate=2,
          sample=False, frame_force=False,
          feature_force=False,
          match_force=False, video_mode=10):
    """Make the first iteration of processing loop: list, compute features and matches
       to split the frames in frame sets.
       Return: path to sets folder and width"""

    # Extract frames
    path_frames = pth_frms(v_id, plylst)
    if frame_force:
        remove(path_frames)
     
    if not os.path.isdir(path_frames):
        xtrct_frames(v_id, plylst, sample, rate)

    # Make iter0 dir
    pth_it0 = pth_iter0(v_id, plylst)
    make_dir(pth_it0)

    # Listing
    width = get_dic_info(v_id, plylst)['width']
    openmvg_list(width, path_frames, pth_it0)

    path_feat = pth_iter0_feats(v_id, plylst)
    path_sfm = os.path.join(pth_it0, 'sfm_data.json')

    # Compute features
    if feature_force or not os.path.isdir(path_feat):
        openmvg_features(path_sfm, path_feat, force=feature_force)

    # Compute  matches
    if match_force or not os.path.isfile(pth_iter0_mtchs(v_id, plylst)):
        openmvg_matches(path_sfm, path_feat, video_mode=video_mode, force=match_force)

    # Make sets
    path_sets = pth_sets(v_id, plylst)
    if not os.path.isdir(path_sets) or feature_force and match_force:
        path_sets = make_sets(v_id, plylst)
        remove_ds_store(path_sets)

    return path_sets, width


def sfm_pipe(pth_set, width, video_mode=None):
    """Function that performs the sfm pipeline given the path to
       a set as generated by make_sets.
       Video mode is set to None to get the most number of vertices.
       Matches are force to be recomputed. """

    frames = os.path.join(pth_set, 'frames')
    features = os.path.join(pth_set, 'features')
    openmvg_list(width=width, pth_frms=frames, pth_out=pth_set)

    path_sfm = pth_sfm(pth_set)
    openmvg_features(pth_sfm=path_sfm, pth_features=features)
    openmvg_matches(pth_sfm=path_sfm, pth_matches=features,
                    force=True,
                    video_mode=video_mode)

    path_incr = os.path.join(pth_set, 'incremental')
    make_dir(path_incr)

    openmvg_incremental(pth_sfm=path_sfm, pth_matches=features, pth_incr=path_incr)
    openmvg_colors(pth_incr=path_incr)
    openmvs_densification(pth_in=path_incr)
    


####################################### Aux functions for parallelisation


def execute_fun_par(target, args_l):
    """ Launch processes in parallel for specified target and list of arguments"""
    for args in args_l:
        Process(target=target, args=args).start()


def list_extract(lst, max_num):
    """ Function used to pop a number of elements from a list equal or less than max_num """

    ret_lst = []
    if len(lst) >= max_num:
        for i in range(max_num):
            ret_lst.append(lst.pop())

    else:  # less elements than max_num
        for i in reversed(range(len(lst))):
            ret_lst.append(lst.pop())

    return ret_lst
####################################### Many videos sequentially


def drain_many_seq(urls, plylst ='',
                   dl_format='bestvideo', rate=1,
                   parallel_tasks=4,
                   sample=False, frame_force=False,
                   feature_force=False,
                   match_force=False, video_mode=30):
    """Process many videos in parallel.
       iter0 are executed in parallel.
       sfm_pipe are executed for each video in parallel but each set for each video is treated sequentially.
       Use : pass a list of urls to be dowloaded, a playlist where to store them. """

    manager = Manager()
    shared_list = manager.list()

    # Download
    while not len(urls) == 0:
        url_batch = list_extract(lst=urls, max_num=parallel_tasks)
        args_yt = [(url, plylst, dl_format) for url in url_batch]

        control_download = Process(target=execute_fun_par, args=(yt_dl, args_yt))
        control_download.start()
        control_download.join()

    playlist = pth_plylst(plylst)
    remove_ds_store(playlist)
    vids_list = os.listdir(playlist)

    # iter0s step
    while not len(vids_list) == 0:
        vids_batch = list_extract(lst=vids_list, max_num=parallel_tasks)
        args_iter0 = [((v_id, plylst, rate,  sample, frame_force, feature_force, match_force, video_mode),
                        shared_list)
                       for v_id in vids_batch]

        control_iter0 = Process(target=execute_fun_par, args=(iter0_seq, args_iter0))
        control_iter0.start()
        control_iter0.join()

    # sfm_pipes step
    while not len(shared_list) == 0:

        sets_batch = list_extract(lst=shared_list, max_num=parallel_tasks)

        control_launch = Process(target=execute_fun_par, args=(sfm_pipe_seq, sets_batch))
        control_launch.start()
        control_launch.join()
        
        

#################### Aux Functions


def iter0_seq(args_iter0, shared_list):
    """Calls iter0 and append the returns to the shared_list"""
    paths_sets, width = iter0(*args_iter0)
    shared_list.append((paths_sets, width))


def sfm_pipe_seq(pth_sets, width):
    """ Executes sfm_pipe sequentially for each set."""
    path_sets = [os.path.join(pth_sets, el) for el in os.listdir(pth_sets)]

    for path_set in path_sets:
        args_sfm = (path_set, width)
        single_execution = Process(target=sfm_pipe, args=args_sfm)
        single_execution.start()
        single_execution.join()


#######################################  Single video in parallel


def drain_one(url, playlist='', 
              dl_format='bestvideo', rate=2, parallel_tasks=4,
              sample=False, frame_force=False,
              feature_force=False,
              match_force=False, video_mode=30):
    """Function to download and process one video.
       Returns path to video folder.
       Launches as many sfm_pipes in parallel as 
       parallel_tasks. 
       Returns path to video folder"""

    v_id, _ = yt_dl(url=url, playlist=playlist,format=dl_format)

    path_sets, width = iter0(v_id=v_id, plylst=playlist,
                             rate=rate,
                             sample=sample, frame_force=frame_force,
                             feature_force=feature_force,
                             match_force=match_force, video_mode=video_mode)

    sfm_pipe_par(path_sets, width, parallel_tasks)
    return pth_vid(v_id, playlist)


def sfm_pipe_par(pth_sets, width, parallel_tasks=4):
    """Executes a number equal to parallel_tasks of 
       sfm_pipe in parallel."""

    pth_sets = [os.path.join(pth_sets, el) for el in os.listdir(pth_sets)]

    while not len(pth_sets) == 0:

        pths = list_extract(lst=pth_sets, max_num=parallel_tasks)
        args_sfm = [(pth, width) for pth in pths]

        batch_execution = Process(target=execute_fun_par, args=(sfm_pipe, args_sfm))
        batch_execution.start()
        batch_execution.join()
