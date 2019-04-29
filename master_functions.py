from functions import *

def capture(url, sample=False):
    ''''Functions that creates the vid directory, download the video
    and extract the frames.'''

    # Create vid dir and download
    yt_dl(url=url)
    v_id = url_to_id(url=url)

    # Extract frames
    frame_xtrct(v_id=v_id, sample=sample)
    return v_id


def iter0(v_id):
    """Function used to make the first iteration of processing loop"""

    # Make iter0 dir
    path_dir = pth_vid_dir(v_id)
    path_iter0 = os.path.join(path_dir, 'iter0')
    make_dir(path_iter0)

    # Listing
    frm_dir = os.path.join(path_dir, 'frames')

    openmvg_list(v_id=v_id, frm_dir=frm_dir, out_dir=path_iter0)

    # Compute features, matches
    path_feat = os.path.join(path_iter0, 'features')
    make_dir(path_feat)

    sfm = 'sfm_data.json'
    path_sfm = os.path.join(path_iter0, sfm)

    openmvg_features(path_sfm=path_sfm, path_features=path_feat)
    openmvg_matches(path_sfm=path_sfm, path_matches=path_feat)


def make_sets(v_id):
    """Used after the iter_0 function ran to separate the frames into sets.
    Return the path the to the sets folder"""

    triangles = split_triangles(mtchs_bin_to_mat(path_mtchs=pth_iter0_mtchs(v_id),
                                                 path_frames=pth_frms(v_id)))

    return move_triangles(triangles=triangles,
                          path_vid=pth_vid_dir(v_id),
                          path_frames=pth_frms(v_id),
                          path_feats=pth_iter0_feats(v_id))



def sfm_pipe(pth_set):
    """Function that performs the sfm pipline given the path to
    a set as generated by make_sets."""
    frames = os.path.join(pth_set, 'frames')
    features = os.path.join(pth_set, 'features')
    v_id = get_v_id(pth_set)
    print(v_id)

    openmvg_list(v_id=v_id, frm_dir=frames, out_dir=pth_set)

    path_sfm = pth_sfm(pth_set)
    openmvg_features(path_sfm=path_sfm, path_features=features)
    openmvg_matches(path_sfm=path_sfm, path_matches=features)

    path_incr = os.path.join(pth_set, 'incremental')
    make_dir(path_incr)
    openmvg_incremental(path_sfm=path_sfm, path_matches=features, path_incr=path_incr)
    openmvg_colors(path_incr=path_incr)